# Email-AI-agent
This agent acts as an intermediate between the receiver and sender. It automates the process of reading mail from the inbox, transforming it using an LLM into the desired output and finally sending the generated output back to the sender.  
Create an .env file since it provides the api key, your email addres, your email password, smtp server and imap server. Use the template given below which could be used to add in your credentials before the project is executed. 
OPENROUTER_API_KEY=" "
EMAIL_ADDRESS=" "
EMAIL_PASSWORD=" "
IMAP_SERVER=imap.gmail.com
SMTP_SERVER=smtp.gmail.com

Use any of your preferred model. Replace the llm list with the desired model, I have a used a free Openrouter compatible model. 

Run "main.py" to execute the program only once, which checks the latest mail in the inbox and then processes it. 

Run "loop.py" to start an endless loop that will check the inbox every 15 seconds.
