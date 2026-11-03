# DBS Stock Market Analytics and Portfolio Management System

## 1. Project Title

**DBS Stock Market Analytics and Portfolio Management System**

## 2. Problem Statement

Investors often find it difficult to analyse historical stock market data, track stock performance, manage their portfolios, and make informed investment decisions. Managing large amounts of historical financial data also creates challenges in data storage, retrieval, and performance.

This project aims to develop a centralized stock market analytics and portfolio management system that uses relational and time-series databases to efficiently store, manage, and analyse financial market information.

## 3. Abstract

The DBS Stock Market Analytics and Portfolio Management System is designed to help users analyse stock market data and manage their investment portfolios. The system uses PostgreSQL for relational data management and TimescaleDB for handling time-series financial data. It contains historical stock price information for Nifty 50 companies from 1999 to 2026, along with corporate actions such as dividends and stock splits. The project includes database views, stored procedures, triggers, and analytical SQL queries to support efficient data processing and portfolio-related operations. The application also provides a user interface for interacting with the system and viewing relevant financial information.

## 4. Team Members

| S. No. | Name | Register Number |
|---|---|---|
| 1 | [Easwar A P] | [25BCE1512] |
| 2 | [Mohammed Irfan] | [25BCE1462] |
| 3 | [Mohammed Nadeem] | [25BCE1771] |

## 5. Functional Features

- Historical stock market data management for Nifty 50 companies.
- Stock price analysis using historical market records.
- Portfolio creation and management.
- Tracking of stock investments and transactions.
- Corporate action management, including dividends and stock splits.
- Time-series data storage and retrieval using TimescaleDB.
- Relational data management using PostgreSQL.
- Analytical SQL queries for extracting useful financial information.
- Database triggers for automated database operations.
- Stored procedures and views for simplifying complex database operations.
- Frontend interface for interacting with the application.

## 6. Technology Stack

| Component | Technology |
|---|---|
| Relational Database | PostgreSQL 18 |
| Time-Series Database | TimescaleDB |
| Database Containerization | Docker |
| Backend | [Enter backend technology] |
| Frontend | [Enter frontend technology] |
| Programming Language | Python |
| Data Processing | Pandas |
| Version Control | Git and GitHub |

## 7. Database Software and Requirements

### Software Requirements

- PostgreSQL 18
- TimescaleDB (compatible version)
- Docker Desktop
- Python 3.x
- Git
- Node.js and npm (if required by the frontend)
- Required Python packages

### Hardware Requirements

- Minimum 8 GB RAM recommended.
- Stable internet connection for initial setup.
- Sufficient disk space for historical stock market data.

## 8. Database Architecture

The project uses two database systems to handle different types of information.

### PostgreSQL

PostgreSQL manages relational information, including:

- User information
- Portfolio details
- Stock information and related metadata
- Transactions
- Corporate actions
- Other relational records

### TimescaleDB

TimescaleDB handles time-series financial information, particularly historical stock market prices.

Historical stock price records are stored using TimescaleDB hypertables to support efficient time-based data storage and querying.

This architecture allows the application to use PostgreSQL for relational operations while taking advantage of TimescaleDB for historical financial data.

## 9. Database Tables and Relationships

The PostgreSQL database consists of a 13-table schema designed for stock market analytics and portfolio management.

The database includes entities related to:

- Stocks and companies
- Historical market information
- Corporate actions
- Users
- Portfolios
- Investment transactions

The tables are connected using primary keys and foreign keys to maintain referential integrity.

The TimescaleDB implementation stores historical stock price information in time-series format using hypertables.

### Sample Dataset

- 49 Nifty 50 stocks
- 287,310 daily historical price records
- Historical data covering 1999–2026
- 1,653 corporate action events
- Dividend and stock split information

## 10. Application Setup and Execution

### Step 1: Clone the Repository

```bash
git clone https://github.com/easwararun5-dotcom/DBS-Stock-Market-Analytics.git

cd DBS-Stock-Market-Analytics
```

### Step 2: Configure Environment Variables

Create a `.env` file using the provided example.

```bash
cp .env.example .env
```

Configure the required PostgreSQL connection details in the `.env` file.

### Step 3: Start the Databases

Start the PostgreSQL and TimescaleDB services using Docker.

```bash
docker compose up -d
```

Verify that both database services are running before proceeding.

### Step 4: Create the Database Schema

Execute the SQL schema file:

```bash
psql -U <username> -d <database_name> -f sql/01_create_schema.sql
```

### Step 5: Enable TimescaleDB

Ensure that the TimescaleDB extension is enabled in the appropriate database.

```sql
CREATE EXTENSION IF NOT EXISTS timescaledb;
```

Create the required hypertable for historical stock price data as defined in the project implementation.

### Step 6: Load Sample Data

Use the provided Python ingestion script:

```bash
pip install -r requirements.txt

python scripts/ingest_data.py
```

Configure the database connections and data paths before running the ingestion process.

### Step 7: Start the Application

Start the backend and frontend using their respective setup instructions.

**Backend:**
cd backend
python main.py

**Frontend:**
cd frontend
python -m http.server 5500


The application can then be accessed through the configured local development URL.

## 11. Implemented Database Components

The project includes:

- 13 relational database tables.
- 6 analytical database views.
- 7 stored procedures.
- 2 database triggers.
- SQL analytical query suite consisting of 10 files.
- Automated CSV data ingestion pipeline.
- Trigger integration test suite covering 8 scenarios, including live concurrency testing.

## 12. Brief Summary and Implemented Features

The DBS Stock Market Analytics and Portfolio Management System provides a database-driven platform for managing and analysing stock market data. It includes a historical stock price data ingestion pipeline that loads data for 49 Nifty 50 companies, along with corporate action records such as dividends and stock splits. The system uses relational tables to organise stock, price, and corporate action data, supported by analytical views, stored procedures, and triggers. It enables users to perform stock market analysis through SQL queries and maintains data consistency through automated database operations. Testing scripts are also included to verify the analytical queries and trigger functionality.

## 13. Testing Instructions

The project includes database-level testing for validating data operations and trigger behaviour.

Run the following test scripts:

```bash
python scripts/test_queries.py

python scripts/test_triggers.py
```

Verify the following:

- Successful database connectivity.
- Correct table creation and relationships.
- Successful historical data ingestion.
- Correct execution of analytical queries.
- Proper trigger execution.
- Successful TimescaleDB hypertable creation.
- Successful retrieval of time-series records.
- Correct application connectivity with both databases.

## 14. Known Limitations

- Historical data availability depends on the provided dataset.
- Stock market analysis is based on historical information and does not guarantee future market performance.
- Application functionality depends on successful database connectivity.
- Real-time market data availability depends on external data sources, if configured.
- The system is developed primarily as an academic project and is not intended to provide professional investment advice.

## 15. YouTube Demonstration

**Project Demonstration Video:** [Insert YouTube Link Here]

The demonstration covers the application interface, database architecture, PostgreSQL implementation, TimescaleDB implementation, data ingestion, and major functional features.

## 16. Repository

GitHub Repository:

https://github.com/easwararun5-dotcom/DBS-Stock-Market-Analytics

