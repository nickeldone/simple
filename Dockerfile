FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
# Fails with: TypeError: RuleGenerator.__init__() got an unexpected keyword argument 'parser'  
CMD ["python", "main.py"]
