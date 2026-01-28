# Setup Guide

## Prerequisites

- Python 3.10+
- Node.js 18+
- MongoDB (or MongoDB Atlas account)

## Backend Setup

cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

## Frontend Setup

cd frontend
npm install

## Running the Application

[Instructions to be added once projects are initialized]

## Environment Variables

Create a `.env` file in the `backend/` directory:

DEBUG=True
SECRET_KEY=your-secret-key
MONGODB_URI=mongodb://localhost:27017/gameengine
