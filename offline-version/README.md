# SERDIF offline version

## Overview

The SERDIF offline app is a Graphical User Interface (GUI) to link spatiotemporal datasets from a local folder, called `raw`, with events of interest by specifying linkage options like time window and area from the events.

## Setup Instructions

Follow these steps to set up the project and run the application within a virtual environment.

### Step 1: create a virtual environment

Open your terminal (or Command Prompt on Windows) and navigate to your project directory. Create a virtual environment named `myenv`:

```sh
cd /path/to/your/project
python -m venv myenv
```

### Step 2: activate the virtual environment
Windows:
```sh
myenv\Scripts\activate
```
macOS and Linux:
```sh
source myenv/bin/activate
```
### Step 3: install required packages
```sh
pip install -r requirements.txt
```

### Step 4: Run the app
```sh
python app.py
```
