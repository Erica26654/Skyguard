## Project Overview
Skyguard detects aviation operation risks from event text. It extracts multiple risk signals and follows a fixed business priority order:

`Human override > Data conflict > Weather disruption > Capacity stress`

The system classifies risk levels and generates tailored notification drafts for three audiences: internal operators, airport coordinators and passengers.

> Important: This system is only for decision support. All safety-critical operational decisions, such as flight dispatch and release, must be confirmed by qualified aviation staff.

## Dependencies
- Python 3.10+
- pandas
- openpyxl

Install packages:
```bash
pip install pandas openpyxl
```

## File Structure
```
├── run.py               # Main program: signal detection, risk classification, Excel read/write
└── README.md
```

## How to Run
1. Keep `run.py` and `Track 3 Data.xlsx` in the same folder.
2. Open your terminal in this directory.
3. Execute:
```bash
python run.py
```
4. The program will print reasoning logs showing detected signals and risk results.
5. Final outputs will be written into a new sheet inside the Excel file.

## Known Limitations
- Risk detection relies on keyword matching, limited synonym coverage
- Airport baseline values are simulated, not real production data
- Concurrent event processing is not supported

## Development Note
We used an AI assistant for coding assistance, text revision and document drafting. The core aviation risk rules were defined by our team, and all outputs were manually verified.
