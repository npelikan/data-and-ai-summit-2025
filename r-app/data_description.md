This dataset contains detailed information about Tour de France races across multiple years, with data on riders, stages, and results.

## Column Descriptions

### edition
- **Type**: Double (numeric)
- **Description**: The edition number of the Tour de France.
- **Example**: 1 for the first Tour de France in 1903, 67 for the 1980 edition, etc.

### year
- **Type**: Double (numeric)
- **Description**: The year in which the Tour de France took place.
- **Example**: 1903, 1980, etc.

### start_date
- **Type**: Date
- **Description**: The date when a particular stage started.
- **Format**: YYYY-MM-DD
- **Example**: 1903-07-01

### stage_results_id
- **Type**: Character
- **Description**: Unique identifier for each stage of the race.
- **Format**: \"stage-X\" where X is the stage number. Some stages have subdivisions indicated by letters (e.g., \"stage-7a\").
- **Example**: \"stage-1\", \"stage-7a\", \"stage-0\" (likely a prologue stage)

### rank
- **Type**: Character
- **Description**: The finishing position of a rider in a particular stage.
- **Example**: \"1\" for first place, \"2\" for second place, etc.

### time
- **Type**: Double (numeric)
- **Description**: The time taken for a stage. The stage winner is recorded as their full time. Other finishers are recorded as the time elapsed since the winner.
- **Example**: 63913, 55, 2099, etc.

### rider
- **Type**: Character
- **Description**: The name of the cyclist.
- **Format**: Usually \"Last_Name First_Name\"
- **Example**: \"Garin Maurice\", \"Hinault Bernard\"

### age
- **Type**: Double (numeric)
- **Description**: The age of the rider at the time of the race.
- **Example**: 32, 25, etc.
- **Note**: Contains some NA values for unknown ages.

### team
- **Type**: Character
- **Description**: The team that the rider represented in the race.
- **Example**: \"Renault\", \"TI Raleigh\", etc.
- **Note**: Contains NA values, especially for earlier editions of the race.

### points
- **Type**: Double (numeric)
- **Description**: Points awarded to the rider for the stage for the points classification.
- **Example**: 100, 70, 50, etc.
- **Note**: Contains NA values where points were not awarded or recorded.

### elapsed
- **Type**: Double (numeric)
- **Description**: The total time (in seconds) taken by the rider to complete the stage.
- **Example**: 63913, 63968, etc.

### bib_number
- **Type**: Double (numeric)
- **Description**: The identification number worn by the rider during the race.
- **Example**: 1, 11, 97, etc.
- **Note**: Contains NA values where bib numbers were not recorded, particularly in earlier races.

## Notes

- The dataset contains 255,752 rows, each representing a rider's performance in a specific stage.
- Some values are NA where data was not available, particularly in older editions of the race.
- Time-related values are stored in seconds.
- Stage results with identifiers like \"stage-7a\" and \"stage-7b\" indicate split stages that occurred on the same day.