"""
Goal: Searches for job listings, evaluates relevance based on a CV, and applies

@dev You need to add GEMINI_API_KEY to your environment variables.
Also you have to install PyPDF2 to read pdf files: pip install PyPDF2
and langchain-google-genai: pip install langchain-google-genai
"""

import csv
import os
import sys
from pathlib import Path
import logging
from typing import List, Optional
import asyncio

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from PyPDF2 import PdfReader
from langchain_google_genai import ChatGoogleGenerativeAI # Import Langchain's Gemini integration
from pydantic import BaseModel, SecretStr

from browser_use import ActionResult, Agent, Controller
from browser_use.browser.context import BrowserContext
from browser_use.browser.browser import Browser, BrowserConfig

# Validate required environment variables
load_dotenv()
required_env_vars = ["GEMINI_API_KEY"] # Updated to use GEMINI_API_KEY
for var in required_env_vars:
    if not os.getenv(var):
        raise ValueError(f"{var} is not set. Please add it to your environment variables.")

logger = logging.getLogger(__name__)
# full screen mode
controller = Controller()

# NOTE: This is the path to your cv file
CV = Path.cwd() / '/Users/debabratapanda/PycharmProjects/auto_browser/resume.pdf'

if not CV.exists():
	raise FileNotFoundError(f'You need to set the path to your cv file in the CV variable. CV file not found at {CV}')


class Job(BaseModel):
	title: str
	link: str
	company: str
	fit_score: float
	location: Optional[str] = None
	salary: Optional[str] = None


@controller.action('Save jobs to file - with a score how well it fits to my profile', param_model=Job)
def save_jobs(job: Job):
	with open('jobs.csv', 'a', newline='') as f:
		writer = csv.writer(f)
		writer.writerow([job.title, job.company, job.link, job.salary, job.location])

	return 'Saved job to file'


@controller.action('Read jobs from file')
def read_jobs():
	with open('jobs.csv', 'r') as f:
		return f.read()


@controller.action('Read my cv for context to fill forms')
def read_cv():
	pdf = PdfReader(CV)
	text = ''
	for page in pdf.pages:
		text += page.extract_text() or ''
	logger.info(f'Read cv with {len(text)} characters')
	return ActionResult(extracted_content=text, include_in_memory=True)


@controller.action(
	'Upload cv to element - call this function to upload if element is not found, try with different index of the same upload element',
)
async def upload_cv(index: int, browser: BrowserContext):
	path = str(CV.absolute())
	dom_el = await browser.get_dom_element_by_index(index)

	if dom_el is None:
		return ActionResult(error=f'No element found at index {index}')

	file_upload_dom_el = dom_el.get_file_upload_element()

	if file_upload_dom_el is None:
		logger.info(f'No file upload element found at index {index}')
		return ActionResult(error=f'No file upload element found at index {index}')

	file_upload_el = await browser.get_locate_element(file_upload_dom_el)

	if file_upload_el is None:
		logger.info(f'No file upload element found at index {index}')
		return ActionResult(error=f'No file upload element found at index {index}')

	try:
		await file_upload_el.set_input_files(path)
		msg = f'Successfully uploaded file "{path}" to index {index}'
		logger.info(msg)
		return ActionResult(extracted_content=msg)
	except Exception as e:
		logger.debug(f'Error in set_input_files: {str(e)}')
		return ActionResult(error=f'Failed to upload file to index {index}')


browser = Browser(
	config=BrowserConfig(
		chrome_instance_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
		disable_security=True,
	)
)


async def main():
	ground_task = (
		'You are a highly meticulous and careful LinkedIn job application agent. '
		'Your primary goal is to find and Easy Apply to Data Analyst jobs on LinkedIn, while being extremely cautious and **never** altering pre-filled information in application forms.'
		
		'Here are the detailed steps you MUST follow:'
		
		'1. Initial Setup: Begin by using the `read_cv` action to thoroughly read and understand the content of my CV. This CV is crucial context for understanding my profile and will be used for applications.'
		
		'2. LinkedIn Job Search: Navigate to the LinkedIn Jobs search page.'
		
		'3. Job Search Query:  Perform a job search on LinkedIn for "Data Analyst jobs".'
		
		'4. Apply Filters:  Critically apply the following filters to the search results to narrow down to relevant opportunities:'
			'a) Filter by "Entry level" for job level/experience.'
			'b) **Crucially and most importantly, filter to show ONLY "Easy Apply" jobs.** This is the most important filter for this task.'
		
		'5. Job Listing Iteration: Systematically go through each job listing presented in the filtered search results, one by one.'
		
		'6. Easy Apply Process (For Each Job Listing):'
			'a) Identify if the job has the "Easy Apply" option clearly indicated. **Only proceed if it is an "Easy Apply" job.**'
			'b) Click the "Easy Apply" button to initiate the application process.'
			'c) Application Form Navigation: Carefully proceed through each step or page of the Easy Apply application form. Be extremely attentive to the form content.'
			'd) **Pre-filled Fields - ABSOLUTE RULE: Under NO CIRCUMSTANCES should you change or modify any information that is ALREADY pre-filled in ANY form field.** This is paramount. Pre-filled fields often include my resume, country code, phone number, email, etc.  Leave them EXACTLY as they are. Do not click to edit them unless explicitly instructed otherwise (which is NOT the case in this task).'
			'e) Filling EMPTY Required Fields: If there are any form fields that are clearly marked as "required" (e.g., with an asterisk *) and are EMPTY (not pre-filled), use your best judgment and general knowledge, combined with context from my CV (which you read in step 1), to fill them in appropriately and concisely. Only fill in fields that are truly empty and required. If unsure, leave it blank rather than guessing incorrectly or changing pre-filled data.'
			'f) Multiple/Radio Selects: For multiple choice questions or radio button selections, if an option is already pre-selected, carefully review it and generally leave it as is if it seems reasonable in the context of a job application. If no option is pre-selected and it is required, select the most generally applicable or neutral option. If unsure, prefer to NOT make a selection rather than making a potentially incorrect one (though required fields should ideally be filled).'
			'g) Final Review and Submission: Before submitting each application, perform a final, very careful review of the ENTIRE form. **Re-emphasize and ensure that you have NOT altered any pre-filled information.** Once you are absolutely certain about this, and have filled any genuinely empty required fields reasonably, submit the application.'
			'h) Job Details Saving: After each successful application submission, use the `save_jobs` action to record the job title, company name, and LinkedIn job link to the "jobs.csv" file. This is important for tracking applied jobs.'
		
		'7. Application Target: Continue iterating through job listings and applying to "Easy Apply" jobs until you have applied for at least 50 jobs, or until you have exhausted all relevant "Easy Apply" Data Analyst job listings in the current search results.'
		
		'8. Navigation and Language: You can navigate through the application process by carefully clicking buttons, proceeding to the next steps, and scrolling within pages as needed. Always ensure you remain on the English version of the LinkedIn website throughout the entire process.'
		
		'Important Reminders - Read Carefully:'
		'* **ABSOLUTELY NO CHANGES TO PRE-FILLED FIELDS:** This is the most critical instruction. Never modify pre-filled information.'
		'* **Focus on "Easy Apply" ONLY:**  Only apply to jobs that have the "Easy Apply" option.'
		'* **Careful and Deliberate Actions:** Proceed through each application step deliberately and cautiously. Do not rush.'
		'* **When in Doubt, Err on the Side of Caution:** If you are ever uncertain about what to fill in or whether to change something, it is always better to err on the side of caution and avoid making changes, especially to pre-filled data.'
	 )
	"""ground_task = (
		'You are a professional job finder. '
		'1. Read my cv with read_cv'
		'find 100 ml internships in and save them to a file'
		'search at company:'
	)"""
	tasks = [
		ground_task + '\n' + 'Google',
		# ground_task + '\n' + 'Amazon',
		# ground_task + '\n' + 'Apple',
		# ground_task + '\n' + 'Microsoft',
		# ground_task
		# + '\n'
		# + 'go to https://nvidia.wd5.myworkdayjobs.com/en-US/NVIDIAExternalCareerSite/job/Taiwan%2C-Remote/Fulfillment-Analyst---New-College-Graduate-2025_JR1988949/apply/autofillWithResume?workerSubType=0c40f6bd1d8f10adf6dae42e46d44a17&workerSubType=ab40a98049581037a3ada55b087049b7 NVIDIA',
		# ground_task + '\n' + 'Meta',
	]

	# Initialize Langchain's ChatGoogleGenerativeAI
	model = ChatGoogleGenerativeAI(model="gemini-2.0-flash", google_api_key=os.getenv('GEMINI_API_KEY'))

	agents = []
	for task in tasks:
		agent = Agent(task=task, llm=model, controller=controller, browser=browser) # Pass Langchain Gemini model
		agents.append(agent)

	await asyncio.gather(*[agent.run() for agent in agents])


if __name__ == "__main__":
	asyncio.run(main())