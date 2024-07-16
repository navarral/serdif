# Use an official Python runtime as a parent image
FROM python:3.8.10

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . .

# Update the package lists for package management
RUN apt-get update

# Install required system packages
RUN apt-get install -y binutils libproj-dev ffmpeg gdal-bin libgdal-dev

# Install GeoPandas and its dependencies
RUN pip install 'geopandas[all]'

# Install the netCDF4 package
RUN pip install netCDF4

# Install Python dependencies from requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Install Java for the graph database
RUN apt-get install -y openjdk-11-jdk

# Expose port 8081 for the app
EXPOSE 8081

# Define the command to run the application
CMD ["python", "app.py"]

