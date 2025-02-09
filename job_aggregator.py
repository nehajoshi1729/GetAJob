import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from googlesearch import search
import spacy

nlp = spacy.load("en_core_web_md")


def construct_google_query(job_title, board_domain):
    """
    Returns a Google search query string that limits the search to a specific domain.
    """
    # e.g., 'site:greenhouse.io "Software Engineer"'
    return f'site:{board_domain} "{job_title}"'


def extract_job_details(url):
    """
    Scrapes the job posting page at `url` and returns a dictionary with job details.
    Customize the selectors based on the site you are scraping.
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
    description_elem = soup.find("div", class_="job-description")
    company_elem = soup.find("div", class_="company-name")

    job_details = {
        "title": title.get_text(strip=True) if title else "N/A",
        "company": company_elem.get_text(strip=True) if company_elem else "N/A",
        "date": date_elem.get("datetime") if date_elem and date_elem.has_attr("datetime") else None,
        "description": (
            description_elem.get_text(
                separator=" ",
                strip=True
            ) if description_elem else ""
        ),
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


def similarity_score(text1, text2):
    """
    Compute similarity between two texts using spaCy.
    """
    doc1 = nlp(text1)
    doc2 = nlp(text2)
    return doc1.similarity(doc2)


def find_similar_jobs(reference_job, job_list, threshold=0.8):
    """
    Returns a list of tuples (job, similarity_score) for jobs similar to the reference job.
    Only returns those with a similarity score above the threshold.
    """
    similar_jobs = []
    for job in job_list:
        if job["url"] == reference_job["url"]:
            continue  # Skip the same job
        score = similarity_score(reference_job["description"], job["description"])
        if score >= threshold:
            similar_jobs.append((job, score))
    # Sort the list by similarity score in descending order
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
                    # If a date is present, check if it is recent.
                    # If no date is provided, consider the job valid.
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

    # Example: Use the first job as a reference for similarity search
    if jobs:
        reference_job = jobs[0]
        print("\nFinding jobs similar to the reference job:")
        similar = find_similar_jobs(reference_job, jobs, threshold=0.8)
        if similar:
            for job, score in similar:
                print(f"- {job['title']} at {job['company']} (Similarity: {score:.2f})")
        else:
            print("No similar jobs found above the similarity threshold.")
