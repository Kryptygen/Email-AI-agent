import os
import imaplib
import smtplib
import email
from email.mime.text import MIMEText
from dotenv import load_dotenv
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableSequence
from langchain_openai import ChatOpenAI
from PyPDF2 import PdfReader
import docx
import csv
import json
import tempfile
from PIL import Image
import pytesseract

load_dotenv()

llm = ChatOpenAI(
    openai_api_base="https://openrouter.ai/api/v1",
    openai_api_key=os.environ["OPENROUTER_API_KEY"],
    model="mistralai/devstral-small:free",
    temperature=0.5
)

template = """

Here's a document. Try to answer what the user asked using whatever info you find inside. Keep it concise. 

Document:
\"\"\"
{document}
\"\"\"

User question:
{question}
"""

prompt = PromptTemplate(input_variables=["document", "question"], template=template)
chain = RunnableSequence(prompt | llm | StrOutputParser())

def pdf(path):
    try:
        return "\n".join([pg.extract_text() for pg in PdfReader(path).pages if pg.extract_text()])
    except:
        return "[Error]"

def docxs(path):
    try:
        return "\n".join([para.text for para in docx.Document(path).paragraphs])
    except:
        return "[Error]"

def txt(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except:
        return "[Error]"

def csvx(path):
    try:
        text = []
        with open(path, newline='', encoding="utf-8") as f:
            reader = csv.reader(f)
            for row in reader:
                text.append(", ".join(row))
        return "\n".join(text)
    except:
        return "[Error]"

def jsonx(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return json.dumps(data, indent=2)
    except:
        return "[Error]"
    
def image(path):
    try:
        img = Image.open(path)
        return pytesseract.image_to_string(img)
    except:
        return "[Image could not be processed]"
    
# fetch mail
def fetch():
    mail = imaplib.IMAP4_SSL(os.environ["IMAP_SERVER"])
    mail.login(os.environ["EMAIL_ADDRESS"], os.environ["EMAIL_PASSWORD"])
    mail.select("inbox")
    status, messages = mail.search(None, "UNSEEN")

    if messages[0]:
        email_id = messages[0].split()[-1]
        _, msg_data = mail.fetch(email_id, "(RFC822)")
        raw = msg_data[0][1]
        msg = email.message_from_bytes(raw)
        sender = email.utils.parseaddr(msg["From"])[1]
        subject = msg["Subject"]
        query = ""
        path = None
        for part in msg.walk():
            kind = part.get_content_type()
            dispo = str(part.get("Content-Disposition"))
            
            if kind == "text/plain" and "attachment" not in dispo:
                query = part.get_payload(decode=True).decode(errors="ignore")
            elif "attachment" in dispo:
                filename = part.get_filename()
                if filename and filename.lower().endswith((".pdf", ".docx", ".txt", ".csv", ".json", ".jpg", ".jpeg", ".png")):
                    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(filename)[-1]) as tmp:
                        tmp.write(part.get_payload(decode=True))
                        path = tmp.name
        return sender, subject, query, path
    return None, None, None, None

# respond
def response(subject, query, path):
    query = (query or "").strip()

    #the return message that will be generated if the user does not send neither the message or the attachment
    if not path and not query:
        return """Dear sir/madam,

Thank you for reaching out. However, we couldn’t find any message content or attached document in your email.

Please send us your query or attach a relevant file so we can assist you better.

Best regards,  
Kevin Armaan"""

    # the message which will be GENERATED if only the message exists and no attachment. 
    if not path:
        result = llm.invoke(query).content
        return f"""

        {result}

        """
    ext = os.path.splitext(path)[-1].lower()
    if ext == ".pdf":
        content = pdf(path)
    elif ext == ".docx":
        content = docxs(path)
    elif ext == ".txt":
        content = txt(path)
    elif ext == ".csv":
        content = csvx(path)
    elif ext == ".json":
        content = jsonx(path)
    elif ext in [".jpg", ".jpeg", ".png"]:
        content = image(path)
    else:
        #When there is an attachment in the message but it isn't in any of the file type listed below. 
        return """Dear sir/madam,

Unfortunately, the file format you attached is not supported. Kindly attach PDF, DOCX, TXT, CSV, JSON, JPG, or PNG files.

Best regards,  
Kevin Armaan"""

    if len(content) > 20000:
        content = content[:20000] + "\n\n[Truncated]"

    # If only document is present and no question, still generate a summary-like reply
    if not query:
        query = "Summarize this document."

    result = chain.invoke({
        "document": content,
        "question": query
    })
    #this message is to reply to the sender with the answer from the document that they have queried. 
    return f"""Dear sir/madam,

Thank you for your email. Based on the attached document, here is the response:

{result}

If you have further questions or need additional help, feel free to reply.

Best regards,  
Kevin Armaan"""

def send(to, subject, body):
    msg = MIMEText(body)
    msg["From"] = os.environ["EMAIL_ADDRESS"]
    msg["To"] = to
    msg["Subject"] = "Re: " + subject

    with smtplib.SMTP_SSL(os.environ["SMTP_SERVER"], 465) as server:
        server.login(os.environ["EMAIL_ADDRESS"], os.environ["EMAIL_PASSWORD"])
        server.send_message(msg)

def main():
    sender, subject, body, path = fetch()
    if sender and not sender.startswith("no-reply@"):
        print("Email from:", sender)
        reply = response(subject, body, path)
        print("Generated reply:\n", reply)
        send(sender, subject, reply)
        print("Email sent.")
        if path:
            os.remove(path)
    else:
        print("No unseen mail or skipped.")

if __name__ == "__main__":
    main()