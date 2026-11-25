# Jaybird Yorkville: class capacity control

A Streamlit app for the MMA 830 Pricing Analytics project (Smith School of Business, Queen's University).
For any class (instructor, day and time), it sets booking rules for the three customer types that share
the 38-spot mat room, and shows expected revenue against the maximum possible.

> Student project. Not an official Jaybird tool. Demand values are placeholders until Jaybird booking data is loaded.

## What the app does

| Customer type | Revenue per spot (default) | Rule |
|---|---|---|
| Members | $22 (average per class) | Stop member bookings once **b** members have booked |
| ClassPass | $19 (payout) | Stop ClassPass bookings when available spots = **y** |
| Drop-ins | $32 regular, $25 Happy Hour | Never stopped |

- **ClassPass rule (y):** a spot is kept for drop-ins when drop-in price × the chance a drop-in fills it is more than the ClassPass payout.
- **Member rule (b):** the app calculates expected revenue for every member limit from 0 to 38 and picks the highest.
- **Benchmarks:** maximum revenue = 38 spots × drop-in price; baseline = expected revenue if all member demand is booked first (no member limit, same ClassPass rule). The baseline is a reference point, not current revenue.

Charts: where expected revenue comes from (and the gap to the maximum) and expected revenue at every member limit.

The model is the same as the Excel model (`Jaybird_Capacity_Control_Model.xlsx`); `tests/test_model.py` checks that they agree.

## Project structure

```
app.py                  Streamlit app (layout, branding, charts)
model.py                Capacity control model (no Streamlit code)
data/demand_data.csv    Demand by class: mean and std dev per customer type (placeholder values)
assets/                 Jaybird wordmark
.streamlit/config.toml  Theme colours
tests/test_model.py     Checks the Python model against the Excel model
requirements.txt
```

## Run it locally

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

Run the tests with `pip install pytest` then `pytest`.

## Put it on GitHub

1. Create a new repository on GitHub (for example `jaybird-capacity-app`). Don't add a README, it's already here.
2. In this folder:
   ```bash
   git remote add origin https://github.com/<your-username>/jaybird-capacity-app.git
   git branch -M main
   git push -u origin main
   ```

## Deploy it (Streamlit Community Cloud, free)

1. Go to <https://share.streamlit.io> and sign in with GitHub.
2. Click **Create app**, choose the repository, branch `main` and main file `app.py`.
3. Click **Deploy**. You get a shareable URL for the presentation.

## Loading real booking data

Open the **Demand data** tab to see the data the model uses and import a CSV, or replace `data/demand_data.csv`. The tab also has a button to download the current data as a template. Required columns:

| Column | Example |
|---|---|
| `day` | Monday |
| `time` | 6:30 PM |
| `instructor` | Instructor A |
| `happy_hour` | Yes / No |
| `members_mean`, `members_sd` | 31.8, 7.9 |
| `dropins_mean`, `dropins_sd` | 13.2, 4.6 |
| `classpass_mean`, `classpass_sd` | 7.9, 3.2 |

Means and standard deviations are the number of spots each customer type wants for that class, estimated from booking history.

## Model assumptions

- Demand for each customer type is normally distributed. Within a class, drop-in and ClassPass demand are treated as independent;
  across classes they move together (busy drop-in classes also have high ClassPass demand), which the data captures directly.
- Expected revenue assumes members book first, then ClassPass, then drop-ins. If drop-ins book earlier,
  they take spots ClassPass would have had, so actual revenue would be the same or higher.
- Member revenue per class is an average ($20 to $24 range; $22 used).
