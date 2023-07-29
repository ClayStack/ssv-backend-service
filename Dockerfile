FROM tiangolo/uvicorn-gunicorn-fastapi:python3.8

# SSV CLI tooling
# Update the package index and install the latest version of Node.js
RUN curl -fsSL https://deb.nodesource.com/setup_16.x | bash -
RUN apt-get install -y nodejs

# Remove the old version of Node.js (if installed)
RUN apt-get remove -y nodejs-doc

#RUN apt-get update && apt-get install -y npm
RUN git clone https://github.com/bloxapp/ssv-keys.git
RUN npm install -g yarn
WORKDIR /app/ssv-keys
RUN git checkout v3
RUN yarn install

#RUN apt-get update && apt-get install -y npm
RUN git clone https://github.com/bloxapp/ssv-scanner.git
RUN npm install -g yarn
WORKDIR /app/ssv-scanner
RUN yarn install

# Set the working directory to /app
WORKDIR /app

# Copy the current directory contents into the container at /app
ADD requirements.txt /app

RUN pip3 install -r requirements.txt

COPY src /app