import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from googlesearch import search
import spacy
import PyPDF2

# Load spaCy model (ensure you have en_core_web_md installed)
try:
    nlp = spacy.load("en_core_web_md")
except OSError:
    import spacy.cli

    spacy.cli.download("en_core_web_md")
    nlp = spacy.load("en_core_web_md")


def construct_google_query(job_title, board_domain):
    """
    Returns a Google search query string that limits the search to a specific domain.
    """
    return f'site:{board_domain} "{job_title}"'


def extract_job_details(url):
    """
    Scrapes the job posting page at `url` and returns a dictionary with job details.
    Tries multiple selectors for the job description to support different job board formats.
    """
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
    except Exception as e:
        print(f"Failed to fetch {url}: {e}")
        return None

    soup = BeautifulSoup(response.content, 'html.parser')

    title = soup.find("h1")
    date_elem = soup.find("time")

    # Try multiple selectors for job description
    description_elem = soup.find("div", class_="job-description")
    if not description_elem:
        # Lever job pages often use this class
        description_elem = soup.find("div", class_="posting-content")
    if not description_elem:
        # As a fallback, use the entire body text (not ideal but better than nothing)
        description_elem = soup.find("body")

    description_text = description_elem.get_text(separator=" ",
                                                 strip=True) if description_elem else ""

    company_elem = soup.find("div", class_="company-name")
    company_text = company_elem.get_text(strip=True) if company_elem else "N/A"

    job_details = {
        "title": title.get_text(strip=True) if title else "N/A",
        "company": company_text,
        "date": date_elem.get("datetime") if date_elem and date_elem.has_attr("datetime") else None,
        "description": description_text,
        "url": url,
    }
    return job_details


def is_recent(post_date_str, days_threshold):
    """
    Check if the job posting date is within the given days_threshold.
    Expects the date string in ISO format (YYYY-MM-DD).
    """
    try:
        # Some pages may include time as well so we take only the date part.
        post_date = datetime.strptime(post_date_str[:10], "%Y-%m-%d")
    except Exception as e:
        print(f"Date parsing failed for {post_date_str}: {e}")
        return False

    return datetime.now() - post_date < timedelta(days=days_threshold)


def similarity_score_spacy(text1, text2):
    """
    Compute similarity between two texts using spaCy.
    (Used for non-resume-based similarity.)
    """
    doc1 = nlp(text1)
    doc2 = nlp(text2)
    return doc1.similarity(doc2)


def find_similar_jobs(reference_job, job_list, threshold=0.8):
    """
    Returns a list of tuples (job, similarity_score) for jobs similar to the reference job.
    Only returns those with a similarity score above the threshold.
    Uses spaCy for similarity.
    """
    similar_jobs = []
    for job in job_list:
        if job["url"] == reference_job["url"]:
            continue  # Skip the same job
        score = similarity_score_spacy(reference_job["description"], job["description"])
        if score >= threshold:
            similar_jobs.append((job, score))
    # Sort by similarity score in descending order
    similar_jobs.sort(key=lambda x: x[1], reverse=True)
    return similar_jobs


def search_jobs(job_type, days_threshold):
    """
    Searches for jobs on a list of job boards and returns jobs posted within the days_threshold.
    If a job posting does not have a date, it is considered valid.
    """
    job_boards = [
        "greenhouse.io",
        "jobs.lever.co",
        "boards.greenhouse.io",
        "job-boards.greenhouse.io",
        "jobs.jobvite.com",
    ]

    aggregated_jobs = []

    for board in job_boards:
        query = construct_google_query(job_type, board)
        print(f"Searching with query: {query}")
        try:
            count = 0
            for url in search(query):
                print(f"Found URL: {url}")
                job_details = extract_job_details(url)
                if job_details:
                    # Check posting date if available; if not, consider valid.
                    if (job_details.get("date") and is_recent(job_details["date"],
                                                              days_threshold)) or not job_details.get(
                            "date"):
                        aggregated_jobs.append(job_details)
                count += 1
                if count >= 5:
                    break
        except Exception as e:
            print(f"Error during search for board {board}: {e}")

    return aggregated_jobs


def extract_text_from_pdf(pdf_path):
    """
    Extracts and returns text from a PDF file using PyPDF2.
    """
    text = ""
    try:
        with open(pdf_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    except Exception as e:
        print(f"Failed to extract text from PDF {pdf_path}: {e}")
    return text


def extract_keywords(text):
    """
    Extracts keywords from text using spaCy.
    This function filters for nouns, proper nouns, and adjectives,
    removes stop words, and returns a set of unique lemmas.
    """
    doc = nlp(text)
    keywords = set()
    for token in doc:
        if token.pos_ in ["NOUN", "PROPN", "ADJ"]:
            if not token.is_stop and token.is_alpha:
                keywords.add(token.lemma_.lower())
    return keywords


def match_jobs_to_resume(resume_file, job_list):
    """
    Reads the resume from the given file path (PDF format expected), extracts keywords
    using an ATS-based approach, then calculates a percentage match between the resume and
    each job's description based on keyword overlap (Jaccard similarity). Returns a list of
    jobs sorted by match percentage.
    """
    if not os.path.exists(resume_file):
        print(f"Resume file not found at {resume_file}. Skipping resume-job matching.")
        return []

    # Extract resume text (PDF expected)
    if resume_file.lower().endswith('.pdf'):
        resume_text = extract_text_from_pdf(resume_file)
    else:
        try:
            with open(resume_file, 'r', encoding='utf-8') as f:
                resume_text = f.read()
        except Exception as e:
            print(f"Failed to read resume file {resume_file}: {e}")
            return []

    if not resume_text.strip():
        print("No text could be extracted from the resume.")
        return []

    # Extract keywords from the resume
    resume_keywords = extract_keywords(resume_text)
    if not resume_keywords:
        print("No keywords could be extracted from the resume.")
        return []

    matched_jobs = []
    for job in job_list:
        job_description = job.get("description", "").strip()
        if not job_description:
            continue

        # Extract keywords from the job description
        job_keywords = extract_keywords(job_description)
        if not job_keywords:
            continue

        # Calculate the Jaccard similarity: (intersection / union) * 100
        intersection = resume_keywords.intersection(job_keywords)
        union = resume_keywords.union(job_keywords)
        match_percentage = (len(intersection) / len(union)) * 100 if union else 0

        job["match_percentage"] = round(match_percentage, 2)
        matched_jobs.append(job)

    # Sort jobs by descending match percentage
    matched_jobs.sort(key=lambda x: x["match_percentage"], reverse=True)
    return matched_jobs


if __name__ == "__main__":
    job_type = input("Enter job type (e.g., 'Software Engineer'): ").strip()
    try:
        days_threshold = int(input("Enter the number of days for recent postings (e.g., 2): "))
    except ValueError:
        days_threshold = 1

    print("\nSearching for jobs...")
    jobs = search_jobs(job_type, days_threshold)

    print(f"\nFound {len(jobs)} job postings matching the criteria:")
    for idx, job in enumerate(jobs, 1):
        print(f"{idx}. {job['title']} at {job['company']} ({job['url']})")

    # Example: Use the first job as a reference for similarity search using spaCy (optional)
    if jobs:
        reference_job = jobs[0]
        print("\nFinding jobs similar to the reference job (using spaCy similarity):")
        similar = find_similar_jobs(reference_job, jobs, threshold=0.8)
        if similar:
            for job, score in similar:
                print(f"- {job['title']} at {job['company']} (Similarity: {score:.2f})")
        else:
            print("No similar jobs found above the similarity threshold.")

    # --- ATS-Based Resume Matching ---
    # Ensure your resume PDF is located at the path "resume/resume.pdf"
    resume_path = os.path.join("resume", "resume.pdf")
    print(
        f"\nMatching jobs against your resume at {resume_path} using ATS-based keyword matching...")
    matched_jobs = match_jobs_to_resume(resume_path, jobs)
    if matched_jobs:
        print("\nTop job matches based on your resume:")
        for job in matched_jobs:
            print(
                f"{job['title']} at {job['company']} - Match: {job['match_percentage']}% (URL: {job['url']})")
    else:
        print("No job matches found based on your resume.")