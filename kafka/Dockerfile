# Use the official Python runtime as a parent image
FROM python:3.11.3

# Set the working directory to /app
WORKDIR /Project/kafka

# Install any needed packages specified in requirements.txt
RUN pip install confluent_kafka python-dotenv

# Copy the rest of the application code into the container at /app
COPY . /Project/kafka

# Expose port for the FastAPI app to listen on
EXPOSE 8080

# Define the command to run your FastAPI application when the container starts
CMD ["python", "server.py"]