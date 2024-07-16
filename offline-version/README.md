# SERDIF offline version

## Overview

The SERDIF offline app is a Graphical User Interface (GUI) to link spatiotemporal datasets from a local folder, called `raw`, with events of interest by specifying linkage options like time window and area from the events.

## Setup Instructions

### Prerequisites

- Docker installed on your machine. You can download it from [here](https://www.docker.com/products/docker-desktop).

### Step 1: Building the Docker image 

Navigate to the directory containing the `Dockerfile` and run the following command: 
```sh docker build -t serdif:offline . ```

### Step 2: Running the Docker container

```sh
docker run -p 8081:8081 serdif:offline
```

### Step 3: Accessing the app
Once the container is running, you can access the application in your web browser at: http://localhost:8081

### Stopping the Docker container

To stop the Docker container, you can use the `docker ps` command to find the container ID and then use `docker stop <container id>`:


### Additional Information
-   Ensure that port 8081 is not being used by any other application.
-   If you make changes to the application code, rebuild the Docker image using the `docker build` command mentioned above.


## Contact
This space is administered by:  **Albert Navarro-Gallinad**  -- *PhD Student in Computer Science*  

GitHub: [navarral](https://github.com/navarral)
ORCID: [0000-0002-2336-753X](https://orcid.org/0000-0002-2336-753X)  
