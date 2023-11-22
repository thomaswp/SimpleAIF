# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory to /app
WORKDIR /app

# Copy only the requirements file to the container
COPY ./requirements.txt /app/requirements.txt

# Install any needed packages specified in requirements.txt
RUN pip install --upgrade pip && pip install -r requirements.txt
RUN pip install Gunicorn==20.1.0

# Copy the current directory contents into the container at /app
COPY . /app

# Make port 80 available to the world outside this container
EXPOSE 80

# Define environment variable
ENV FLASK_APP=server/main.py
ENV FLASK_RUN_HOST=0.0.0.0
ENV FLASK_RUN_PORT=80

# Run flask using Gunicorn
# CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:80", "server.main:app"]
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:80", "--keyfile", "ssl/privkey.pem", "--certfile", "ssl/fullchain.pem", "server.main:app"]
