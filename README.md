# BT5110 LeTour
## Project Structure

```text
BT5110-LeTour/
├── data/
│   ├── riders.csv
│   ├── individual_results.csv
│   └── exits.csv
├── src/
│   ├── data_loading.ipynb
│   └── sql/
│       ├── schema.sql
│       ├── drop_tables.sql
│       └── truncate_tables.sql
├── .env
├── .gitignore
├── requirements.txt
└── project dashboard suggested functions.pdf
```

- `data/` — Source datasets for the project. This is omitted from the GitHub repository and should be added in manually.
- `src/data_loading.ipynb` — Processes, validates, and loads data into PostgreSQL.
- `src/sql/schema.sql` — Creates the normalised database tables.
- `src/sql/drop_tables.sql` — Drops all database tables.
- `src/sql/truncate_tables.sql` — Clears all records while preserving the tables.

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/chiabingxuan/BT5110-LeTour.git
cd BT5110-LeTour
```

### 2. Set up the Python environment

Create and activate a virtual environment:

```bash
python -m venv venv
```

Windows (PowerShell):

```powershell
.\venv\Scripts\activate
```

macOS/Linux:

```bash
source venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

### 3. Set up PostgreSQL

Make sure PostgreSQL is installed and running.

Create a database named `LeTour` using pgAdmin or PostgreSQL's command line.

Execute `src/sql/schema.sql` in the `LeTour` database to create the tables.

### 4. Configure environment variables

Create a `.env` file in the project root:

```env
DB_HOST=localhost
DB_PORT=5433
DB_NAME=LeTour
DB_USER=postgres
DB_PASSWORD=your_password
```

Replace the values with your local PostgreSQL configuration. In particular, your PostgreSQL port may be `5432` instead of `5433`.

### 5. Add the datasets

Create a `data/` folder in the project root if it does not exist, and place the following files inside:

```text
riders.csv
individual_results.csv
exits.csv
```

### 6. Load the data

1. Open `src/data_loading.ipynb` in VS Code or Jupyter.
2. Select the Python interpreter/kernel from the virtual environment.
3. Run the notebook from the `src/` directory so that its relative data paths resolve correctly.
4. Run all cells to process, validate, and insert the data into PostgreSQL.

## Resetting the Database

To remove all records without deleting the tables, execute:

```text
src/sql/truncate_tables.sql
```

To delete all tables, execute:

```text
src/sql/drop_tables.sql
```

After dropping the tables, rerun `schema.sql` before loading the data.

**Note:** The data-loading notebook inserts records directly, so clear the existing data before rerunning the insertion step to avoid primary-key conflicts.