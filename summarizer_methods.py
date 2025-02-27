import os

import PyPDF2
import tiktoken
from openai import OpenAI
from config import API_KEY

# Initialize OpenAI client
client = OpenAI(
    api_key=f"{API_KEY}"
)

# Constants
MODEL = "gpt-3.5-turbo-0125"
TEMPERATURE = 0.2  # Lowered temperature for more factual responses
MAX_TOKENS = 1000
MODEL_TOKEN_LIMIT = 16385
SAFETY_MARGIN = 1000


# System message for the OpenAI model - completely rewritten for extraction focus
SYSTEM_MESSAGE = """
You are an expert academic content analyzer whose sole purpose is to extract and organize information 
from academic texts. Your role is strictly to identify and organize what is ACTUALLY in the text.

IMPORTANT RULES:
1. ONLY include information that is explicitly present in the provided text
2. NEVER generate content beyond what's in the text
3. Maintain the document's original terminology and concepts
4. Organize content hierarchically exactly as it appears in the source material
"""


#helper functions: 


def count_tokens(text):
    """Count tokens in provided text using the appropriate tokenizer."""
    tokenizer = tiktoken.encoding_for_model(MODEL)
    return len(tokenizer.encode(text))





def read_pdf(file=None):
    """Read a PDF file and extract its text content."""
    if file is None:
        file = input("What is the book/document you want to summarize?\n\t")
    file_path = os.path.join(os.getcwd(), "uploaded_pdfs", f"{file}")
    
    try:
        with open(file_path, "rb") as file:
            reader = PyPDF2.PdfReader(file)
            total_pages = len(reader.pages)
            text = ""
            #choice = input(f"Do you want to read all {total_pages} pages? (y/n) \n\t").strip().lower()
            for page in reader.pages:
                    text += page.extract_text()
            # 
            # if choice == "y":
            #     #print(f"Reading {total_pages} pages...\n")
            #     for page in reader.pages:
            #         text += page.extract_text()
            # else:
            #     start_page = int(input("What page do you want to start from? \n\t"))
            #     end_page = int(input("What page do you want to end with? \n\t"))
                
            #     if 1 <= start_page <= end_page <= total_pages:
            #         #print(f"Reading pages {start_page} to {end_page}...\n")
            #         for page_num in range(start_page-1, end_page):
            #             text += reader.pages[page_num].extract_text()
            #     else:
            #         #print(f"Invalid page range. Please specify pages between 1 and {total_pages}.")
            #         return None
            
            return text
    except FileNotFoundError:
        print(f"File not found: {file_path}")
        print("Please make sure the file is in the correct directory.")
    except Exception as e:
        print(f"An error occurred: {e}")
    
    return None





def chunk_text(text, max_chunk_size):
    """Split text into chunks of specified token size."""
    tokenizer = tiktoken.encoding_for_model(MODEL)
    tokens = tokenizer.encode(text)
    
    chunks = []
    for i in range(0, len(tokens), max_chunk_size):
        chunk_tokens = tokens[i:i + max_chunk_size]
        chunks.append(tokenizer.decode(chunk_tokens))
    
    return chunks




#api call is completed here
def process_prompt(prompt=None):
    """Process a prompt"""
    
    messages = [
        {"role": "system", "content": SYSTEM_MESSAGE},
        {"role": "user", "content": prompt}
    ]
    
    completion = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=TEMPERATURE,
        max_tokens=MAX_TOKENS
    )
    return completion.choices[0].message.content






#prompts


def generate_extraction_prompt(chunk_text, previous_headings=None):
    """Create prompt for content extraction and organization."""
    
    context_instruction = ""
    if previous_headings: 
        context_instruction = f"""
        For context, here are the main headings extracted from previous chunks:
        {previous_headings}
        
        Try to organize this chunk's content to fit with these existing headings where appropriate,
        but ONLY if the content in this chunk actually belongs under those headings.
        """
    
    return f"""
    TASK: Carefully read the following text and extract its factual content into a structured outline.
    
    {context_instruction}
    
    EXTRACTION RULES:
    1. Create a hierarchical outline with:
       - Main topics (use ## format)
       - Subtopics (use ### format)
       - Key points as bullet points (use - format)
    
    2. CRITICAL: ONLY include information that ACTUALLY EXISTS in the provided text
    
    3. Use the EXACT terminology and concepts from the text
    
    4. If the text mentions specific examples, definitions, or metrics, include them
    
    5. Maintain the logical flow and organization of the original content

    6. CRITICAL: OMIT BIBLIOGRAPHIC LIKE CONTENT
    
    TEXT TO ANALYZE:
    {chunk_text}
    """


def generate_answers_prompt(chunk_text, question):
    """Create prompt for content extraction and answering the question."""

    
    return f"""
    TASK: Carefully read the following text and question and use the factual content from the text to answer the question
    
    ANSWERING RULES:
    1. Create an answer in a continous paragraph:
       -keep paragraph concise
    
    2. CRITICAL: ONLY include information that ACTUALLY EXISTS in the provided text
    
    3. Use the EXACT terminology and concepts from the text
    
    4. If the text mentions specific examples, definitions, or metrics, include them
    
    5. Maintain the logical flow and organization of the original content

    6. CRITICAL: OMIT BIBLIOGRAPHIC LIKE CONTENT
    
    TEXT TO ANALYZE:
    {chunk_text}

    QUESTION TO ANSWER:
    {question}
    """

def generate_refined_answer(answer):
    """Create prompt for refining the answer."""
    
    return f"""
    TASK: Carefully read the following text and reduce the answer to the most key points
    
    ANSWERING RULES:
    1. Create an answer in a continous paragraph:
       -keep paragraph concise
    
    2. CRITICAL: ONLY include information that ACTUALLY EXISTS in the provided text
    
    3. Use the EXACT terminology and concepts from the text
    
    4. If the text mentions specific examples, definitions, or metrics, include them
    
    5. Maintain the logical flow and organization of the original content

    6. CRITICAL: OMIT BIBLIOGRAPHIC LIKE CONTENT
    
    TEXT TO ANALYZE:
    {answer}


    """











#get summary helpers

def extract_main_headings(outline):
    """Extract main headings from an outline for context."""
    headings = []
    for line in outline.split('\n'):
        if line.strip().startswith('## '):
            headings.append(line.strip())
    return '\n'.join(headings)







def organize_sections(outlines):
    """Organize sections from multiple outline segments into a coherent structure."""
    if not outlines:
        return "No content was extracted from the document."
    
    # Extract all headings and their content
    document_structure = {}
    current_h2 = None
    current_h3 = None
    
    for outline in outlines:
        for line in outline.split('\n'):
            line = line.strip()
            if not line:
                continue
                
            # Check for main heading (H2)
            if line.startswith('## '):
                current_h2 = line[3:].strip() #gather heading
                current_h3 = None
                if current_h2 not in document_structure:
                    document_structure[current_h2] = {"content": [], "subsections": {}}
            
            # Check for subheading (H3)
            elif line.startswith('### '):
                if current_h2:
                    current_h3 = line[4:].strip() 
                    if current_h3 not in document_structure[current_h2]["subsections"]:
                        document_structure[current_h2]["subsections"][current_h3] = []
            
            # Handle bullet points and other content
            elif line.startswith('- ') or line.startswith('* '):
                if current_h3 and current_h2:
                    # Check for duplicates before adding
                    if line not in document_structure[current_h2]["subsections"][current_h3]:
                        document_structure[current_h2]["subsections"][current_h3].append(line)
                elif current_h2:
                    if line not in document_structure[current_h2]["content"]:
                        document_structure[current_h2]["content"].append(line)
    
    # Generate final organized outline
    organized_outline = []
    
    # Add title
    
    if current_h2:
        first_topic = list(document_structure.keys())[0]
        title_subject = first_topic
        
        organized_outline.append(f"{title_subject}")
    else:
        organized_outline.append(f"#")
    
    # Add content organized by sections
    header_count=1
    alphabet= ["a","b","c","d","e","f","g","h","i","j","k","l","m","n","o","p","q","r","s","t","u","v","w","x","y","z"]
    sub_header_count=0
    next_is_tabbed= False
    for h2, section in document_structure.items():
        organized_outline.append(f"\n{header_count}. {h2}")
        
        # Add direct content under h2
        for item in section["content"]:
            organized_outline.append("\t"+item)
        
        # Add all h3 subsections
        for h3, content in section["subsections"].items():
            if content:  # Only add subsections that have content
                if sub_header_count<26:
                    organized_outline.append(f"\n\t{alphabet[sub_header_count]}. {h3}")
                else:
                    organized_outline.append(f"\n\t{sub_header_count}. {h3}")
                for item in content:
                    if "**" in item:
                        next_is_tabbed=True
                    if next_is_tabbed:
                        organized_outline.append("\t\t\t"+ item)
                        next_is_tabbed=False
                    else: 
                        organized_outline.append("\t\t"+ item)

                sub_header_count+=1
        sub_header_count=0
        header_count+=1
    
    return "\n".join(organized_outline)





def file_handler(file):
    # Read PDF if text not provided
    text = read_pdf(file)
    if not text:
        return
    
     # Calculate available tokens for chunks
    base_tokens = count_tokens(SYSTEM_MESSAGE) + count_tokens(generate_extraction_prompt("", None)) + SAFETY_MARGIN + MAX_TOKENS
    chunk_size = MODEL_TOKEN_LIMIT - base_tokens
    
    # Chunk the text
    chunks = chunk_text(text, chunk_size)
    print(f"Processing document in {len(chunks)} chunks...")
    return chunks






def get_summary(file=None):
    
    """Main function to generate an outline from text."""
   

    chunks=file_handler(file)

    # Process each chunk with context from previous chunks
    outline_segments = []
    previous_headings = None
    
    for i, chunk in enumerate(chunks, 1):
        print(f"Processing chunk {i}/{len(chunks)}...")
        outline = process_prompt(generate_extraction_prompt(chunk, previous_headings))
        
        if outline:
            outline_segments.append(outline)
            # Extract headings for context in next chunk
            previous_headings = extract_main_headings(outline)
    
    # Organize outline segments
    #print("Organizing content...")
    organized_outline = organize_sections(outline_segments)
    
    
    # print("\n" + "="*50 + "\n")
    # print(organized_outline)
    formatted_output = organized_outline.replace("\n", "<br>")
    formatted_output = organized_outline.replace("\t", "&nbsp;&nbsp;&nbsp;&nbsp;")

    formatted_output = f"<pre>{organized_outline}</pre>"
    return formatted_output
    
    
def get_answers(question,file):    
    chunks=file_handler(file)
    #put prompt call here
    answer=""
    for i, chunk in enumerate(chunks, 1):
        print(f"Processing chunk {i}/{len(chunks)}...")
        prompt= generate_answers_prompt(chunk, question)
        chunk_answer = process_prompt(prompt)  
        
        if chunk_answer:
            answer+=chunk_answer

     # Calculate available tokens for prompt
    base_tokens = count_tokens(SYSTEM_MESSAGE) + count_tokens(generate_refined_answer("")) + SAFETY_MARGIN + MAX_TOKENS
    answer_size = MODEL_TOKEN_LIMIT - base_tokens

    #reduces answer to fit amount of tokens for model to process
    tokenizer = tiktoken.encoding_for_model(MODEL)
    tokens = tokenizer.encode(answer)
    answer= tokenizer.decode(tokens[0:answer_size])
   

    prompt= generate_refined_answer(answer)
    refined_answer= process_prompt(prompt)
    #print("\n"+refined_answer)
    formatted_output = f"<pre>{refined_answer}</pre>"
    return refined_answer
        
    



#print(get_summary("chapter1_comp333.pdf"))
#if __name__ == "__main__":
    # get_summary()
    # while input("Do you have any questions? (y/n)\n\t")=="y":
    #     get_answers(input("Ask me a question:\n\t"))
    