import random
import string
import spacy
from fastapi import FastAPI, File, UploadFile, Form, Request  # Ensure Request is imported here
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import pdfplumber
import uvicorn
from spacy.lang.en.stop_words import STOP_WORDS

app = FastAPI(debug=True)  # Set debug mode to True

# Load spaCy model
nlp = spacy.load('en_core_web_sm')

templates = Jinja2Templates(directory="templates")

def clean_text(text):
    """Clean the text by removing punctuation and spaces."""
    return text.translate(str.maketrans('', '', string.punctuation)).replace(" ", "")

# Function to generate MCQs for a sentence
def generate_mcq(sentence):
    """Generate MCQs for a sentence."""
    doc = nlp(sentence)
    keywords = [token.text for token in doc if token.pos_ in ('NOUN', 'VERB', 'PROPN', 'ADJ')]
    
    # If no keywords are found, use fallback
    if not keywords:
        keywords = [word for word in sentence.split() if word.lower() not in STOP_WORDS and word.isalpha()]

    correct_answer = random.choice(keywords)
    
    # Generate distractors
    unique_words = [token.text for token in nlp(sentence) if token.text != correct_answer]
    distractors = random.sample(unique_words, 3)

    options = distractors + [correct_answer]
    random.shuffle(options)

    return {
        "question": sentence.replace(correct_answer, "______", 1), 
        "options": options,
        "answer": correct_answer,
        "answer_option": options.index(correct_answer) + 1 
    }

def extract_text_from_pdf(pdf_file):
    """Extract text from a PDF file."""
    with pdfplumber.open(pdf_file) as pdf:
        text = ""
        for page in pdf.pages:
            text += page.extract_text()
    return text

@app.post("/generate_mcqs/")
async def generate_mcqs(request: Request,file: UploadFile = File(None), text: str = Form(None)):
    # If a file is uploaded, process it
    if file:
        if file.filename.endswith('.pdf'):
            text = extract_text_from_pdf(file.file)
        elif file.filename.endswith('.txt'):
            content = await file.read()
            text = content.decode("utf-8", errors="ignore")
        else:
            return {"error": "Invalid file type. Please upload a .txt or .pdf file."}
    
    # If no file is uploaded, check if text is provided in the form
    if not file and not text:
        return {"error": "No file or text provided. Please provide text or upload a .txt/.pdf file."}
    
    # If text is provided (either through form or after file extraction), process it
    if text:
        # Tokenize the text into sentences
        doc = nlp(text)
        sentences = [sent.text.strip() for sent in doc.sents]

        # Generate MCQs
        mcqs = [generate_mcq(sentence) for sentence in sentences[:5]]  # Limit to first 5 questions

        # Render MCQs in the new template
        return templates.TemplateResponse("mcq_page.html", {"request": request, "mcqs": mcqs})
    
    # If we reach here, it means no valid input (file or text) has been provided
    return {"error": "Invalid input. Please upload a valid file (.txt or .pdf) or provide text."}

@app.get("/", response_class=HTMLResponse)
async def read_index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# Run the application using uvicorn if the script is executed directly
if __name__ == "__main__":
    # Ensure uvicorn is running with the app
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=True)
