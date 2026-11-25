"""Jaybird Yorkville - class capacity control (MMA 830 student project)."""
from datetime import datetime
from pathlib import Path

import sys

import altair as alt
import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent))
from model import CAPACITY, solve_row

HERE = Path(__file__).parent
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
REQUIRED = ["day", "time", "instructor", "happy_hour", "members_mean", "members_sd",
            "dropins_mean", "dropins_sd", "classpass_mean", "classpass_sd"]

# Brand: ink, paper, clay and bronze from jaybirdjaybird.com. Chart hues are stronger earth tones
# (terracotta, teal, ochre) validated for colour-blind separation and contrast on the paper background.
INK, PAPER, CLAY, BRONZE, MUTED, GRID = "#161414", "#F4F4F4", "#AC8973", "#806435", "#6B6461", "#E4E1DD"
SERIES = {"Members": "#B48223", "ClassPass": "#007C9E", "Drop-ins": "#A3542B"}
GAP = "#D9D5D0"

st.set_page_config(page_title="Jaybird | Capacity Control", page_icon="◐", layout="wide")

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@500;600&family=Montserrat:wght@400;500;600&display=swap');
html, body, [class*="css"], .stMarkdown, .stText, label, input, select, button {{ font-family: 'Montserrat', sans-serif; }}
h1, h2, h3, h4 {{ font-family: 'Cormorant Garamond', serif !important; font-weight: 500 !important; color: {INK}; letter-spacing: .01em; }}
.jb-eyebrow {{ font-size: .72rem; letter-spacing: .14em; text-transform: uppercase; color: {BRONZE}; font-weight: 600; margin-bottom: .2rem; }}
.jb-banner {{ background: {BRONZE}; color: #fff; text-align: center; font-size: .7rem; letter-spacing: .14em;
              text-transform: uppercase; padding: .35rem; margin: -1rem -1rem 1.2rem -1rem; }}
.jb-card {{ background: #fff; border: 1px solid {GRID}; padding: 1.1rem 1.2rem; height: 100%; }}
.jb-card .num {{ font-family: 'Cormorant Garamond', serif; font-size: 2.6rem; line-height: 1; color: {INK}; margin: .35rem 0 .5rem; }}
.jb-card .rule {{ font-size: .88rem; color: {INK}; }}
.jb-card .swatch {{ display: inline-block; width: 10px; height: 10px; border-radius: 2px; margin-right: 6px; vertical-align: middle; }}
.jb-note {{ font-size: .78rem; color: {MUTED}; }}
div[data-testid="stMetricValue"] {{ font-family: 'Cormorant Garamond', serif; font-size: 2.2rem; color: {INK}; }}
div[data-testid="stMetricLabel"] p {{ text-transform: uppercase; letter-spacing: .1em; font-size: .7rem; color: {MUTED}; }}
section[data-testid="stSidebar"] {{ background: #ECEAE7; }}
</style>
""", unsafe_allow_html=True)


THEME = {"config": {
    "background": PAPER, "font": "Montserrat, Helvetica Neue, Arial, sans-serif",
    "view": {"stroke": None},
    "axis": {"labelColor": MUTED, "titleColor": MUTED, "gridColor": GRID, "domainColor": GRID,
             "tickColor": GRID, "labelFontSize": 11, "titleFontSize": 11, "titleFontWeight": 500},
    "legend": {"labelColor": INK, "titleColor": MUTED, "labelFontSize": 11, "titleFontSize": 11, "orient": "top"},
    "title": {"font": "Montserrat, Helvetica Neue, Arial, sans-serif", "color": INK, "fontSize": 13, "fontWeight": 600, "anchor": "start"},
}}
if hasattr(alt, "theme") and hasattr(alt.theme, "register"):      # Altair 5.5 and newer
    alt.theme.register("jaybird", enable=True)(lambda: alt.theme.ThemeConfig(THEME))
else:                                                              # older Altair
    alt.themes.register("jaybird", lambda: THEME)
    alt.themes.enable("jaybird")


# Work on older and newer Streamlit versions (newer ones use width="stretch", older ones use_container_width).
def show_chart(chart):
    try:
        st.altair_chart(chart, theme=None, width="stretch")
    except TypeError:
        st.altair_chart(chart, theme=None, use_container_width=True)


def show_table(data, **kwargs):
    try:
        st.dataframe(data, width="stretch", **kwargs)
    except TypeError:
        st.dataframe(data, use_container_width=True, **kwargs)


def columns(spec, **kwargs):
    try:
        return st.columns(spec, **kwargs)
    except TypeError:
        kwargs.pop("vertical_alignment", None)
        return st.columns(spec, **kwargs)


def money(x):
    """$32 for whole dollars, $19.50 otherwise."""
    return f"${x:,.0f}" if abs(x - round(x)) < 0.005 else f"${x:,.2f}"


def time_key(t):
    return datetime.strptime(t.strip(), "%I:%M %p")


@st.cache_data
def load_default():
    return pd.read_csv(HERE / "data" / "demand_data.csv")


# ------------------------------------------------------------------ header
st.markdown('<div class="jb-banner">Yorkville · Class capacity control</div>', unsafe_allow_html=True)
left, right = columns([1, 2], vertical_alignment="bottom")
with left:
    st.image(str(HERE / "assets" / "jaybird_wordmark.png"), width=260)
with right:
    st.markdown('<div class="jb-eyebrow" style="text-align:right">MMA 830 Pricing Analytics · student project · not an official Jaybird tool</div>',
                unsafe_allow_html=True)

tab_model, tab_data = st.tabs(["Capacity model", "Demand data"])

# ------------------------------------------------------------------ demand data tab (runs first so the model uses the loaded data)
with tab_data:
    st.markdown("## Demand data")
    st.markdown('<div class="jb-note">For each class (day, time and instructor), the average number of spots each customer type wants and how '
                'much that varies (standard deviation). The model uses these to calculate the booking rules. Import an export from '
                'Jaybird\'s booking system to replace the placeholder values.</div>', unsafe_allow_html=True)
    st.write("")
    up_col, info_col = st.columns([3, 2], gap="large")
    with up_col:
        upload = st.file_uploader("Import demand data (CSV)", type="csv", key="demand_upload",
                                  help="Needs the same columns as the template. Remove the file to go back to the placeholder data.")
    df, source = load_default(), "Placeholder data (synthetic values for the toy model)"
    if upload is not None:
        new = pd.read_csv(upload)
        missing = [c for c in REQUIRED if c not in new.columns]
        if missing:
            up_col.error(f"Missing columns: {', '.join(missing)}. Still using the placeholder data.")
        else:
            df, source = new, f"Imported: {upload.name}"
            up_col.success(f"Loaded {len(df)} classes from {upload.name}.")
    with info_col:
        st.markdown(f'<div class="jb-eyebrow">Data in use</div><div class="rule">{source}</div>'
                    f'<div class="jb-note">{len(df)} classes · {df.instructor.nunique()} instructors · {df.day.nunique()} days</div>',
                    unsafe_allow_html=True)
        st.download_button("Download this data as a CSV template", df.to_csv(index=False).encode(), "demand_data.csv", "text/csv")

    f1, f2, _ = st.columns([1, 1, 2])
    day_f = f1.selectbox("Filter by day", ["All days"] + [d for d in DAYS if d in set(df.day)], key="data_day")
    inst_f = f2.selectbox("Filter by instructor", ["All instructors"] + sorted(df.instructor.unique()), key="data_inst")
    show = df.copy()
    if day_f != "All days":
        show = show[show.day == day_f]
    if inst_f != "All instructors":
        show = show[show.instructor == inst_f]
    show = show.assign(total=show.members_mean + show.dropins_mean + show.classpass_mean,
                       _d=show.day.map({d: i for i, d in enumerate(DAYS)}), _t=show.time.map(time_key))
    show = show.sort_values(["_d", "_t", "instructor"]).drop(columns=["_d", "_t"])
    num = lambda label: st.column_config.NumberColumn(label, format="%.1f")
    show_table(show, hide_index=True, height=520,
                 column_order=["day", "time", "instructor", "happy_hour", "members_mean", "members_sd", "classpass_mean",
                               "classpass_sd", "dropins_mean", "dropins_sd", "total"],
                 column_config={"day": "Day", "time": "Time", "instructor": "Instructor", "happy_hour": "Happy Hour",
                                "members_mean": num("Members: mean"), "members_sd": num("Members: std dev"),
                                "classpass_mean": num("ClassPass: mean"), "classpass_sd": num("ClassPass: std dev"),
                                "dropins_mean": num("Drop-ins: mean"), "dropins_sd": num("Drop-ins: std dev"),
                                "total": num("Total mean demand")})
    st.markdown(f'<div class="jb-note">Showing {len(show)} of {len(df)} classes. Capacity is {CAPACITY} spots per class; '
                'a total mean demand above that means the class is expected to be oversubscribed.</div>', unsafe_allow_html=True)

# ------------------------------------------------------------------ sidebar
with st.sidebar:
    st.markdown('<div class="jb-eyebrow">Select a class</div>', unsafe_allow_html=True)
    instructor = st.selectbox("Instructor", sorted(df.instructor.unique()))
    days = [d for d in DAYS if d in set(df.day)]
    day = st.selectbox("Day", days)
    times = sorted(df[(df.day == day) & (df.instructor == instructor)].time.unique(), key=time_key)
    time = st.selectbox("Class time", times, index=times.index("6:30 PM") if "6:30 PM" in times else 0)

    st.markdown('<div class="jb-eyebrow">Revenue per spot ($)</div>', unsafe_allow_html=True)
    prices = {
        "member": st.number_input("Member (average per class)", 0.0, 100.0, 22.0, 0.5),
        "classpass": st.number_input("ClassPass payout", 0.0, 100.0, 19.0, 0.5),
        "dropin": st.number_input("Drop-in, regular class", 0.0, 100.0, 32.0, 0.5),
        "dropin_happy_hour": st.number_input("Drop-in, Happy Hour class", 0.0, 100.0, 25.0, 0.5),
    }

row = df[(df.day == day) & (df.time == time) & (df.instructor == instructor)].iloc[0]
res = solve_row(row, prices)
hh = str(row.happy_hour).strip().lower() == "yes"
r_D = prices["dropin_happy_hour"] if hh else prices["dropin"]

# ------------------------------------------------------------------ capacity model tab
with tab_model:
    st.markdown(f"## {instructor} · {day} {time}{' · Happy Hour' if hh else ''}")
    st.markdown(f'<div class="jb-note">Expected demand: {row.members_mean:.1f} members, {row.classpass_mean:.1f} ClassPass, '
                f'{row.dropins_mean:.1f} drop-ins for {CAPACITY} spots.</div>', unsafe_allow_html=True)
    st.write("")

    # ------------------------------------------------------------------ booking rules
    st.markdown('<div class="jb-eyebrow">Booking rules for this class</div>', unsafe_allow_html=True)
    member_rule = ("No member limit needed: members can book any available spot." if res.member_limit >= CAPACITY
                   else f"Stop member bookings once <b>{res.member_limit}</b> members have booked.")
    cards = [("Members", res.member_limit if res.member_limit < CAPACITY else "No limit", member_rule),
             ("ClassPass", res.classpass_protect, f"Stop ClassPass bookings when available spots = <b>{res.classpass_protect}</b>."),
             ("Drop-ins", "Always", "Never stopped: drop-ins can book any available spot.")]
    for col, (label, num, rule) in zip(st.columns(3), cards):
        col.markdown(f'<div class="jb-card"><div class="jb-eyebrow"><span class="swatch" style="background:{SERIES[label]}"></span>{label}</div>'
                     f'<div class="num">{num}</div><div class="rule">{rule}</div></div>', unsafe_allow_html=True)
    st.markdown('<div class="jb-note" style="margin-top:.5rem">The rules count bookings and available spots, so they work in any booking order.</div>',
                unsafe_allow_html=True)
    st.write("")

    # ------------------------------------------------------------------ expected vs maximum
    st.markdown('<div class="jb-eyebrow">Expected revenue vs baseline and maximum</div>', unsafe_allow_html=True)
    baseline = float(res.revenue_by_limit[CAPACITY])
    gain = res.expected_revenue - baseline
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Expected revenue per class", f"${res.expected_revenue:,.0f}",
              delta=f"+${gain:,.0f} vs baseline" if gain >= 0.5 else "Same as baseline",
              delta_color="normal" if gain >= 0.5 else "off")
    m2.metric("Baseline: all members first", f"${baseline:,.0f}")
    m3.metric("Maximum revenue", f"${res.max_revenue:,.0f}")
    m4.metric("Expected as % of maximum", f"{res.pct_of_max:.0%}")
    m5.metric("Expected empty spots", f"{res.expected_empty:.1f}")
    st.markdown('<div class="jb-note">Baseline = expected revenue if all member demand is booked first (no member limit), '
                'with the same ClassPass rule. It shows what the member limit adds; it is not Jaybird\'s current revenue. Maximum = all spots sold to drop-ins.</div>',
                unsafe_allow_html=True)
    st.write("")

    parts = pd.DataFrame([
        {"Source": "Members", "Revenue": prices["member"] * res.expected_members, "Spots": res.expected_members},
        {"Source": "ClassPass", "Revenue": prices["classpass"] * res.expected_classpass, "Spots": res.expected_classpass},
        {"Source": "Drop-ins", "Revenue": r_D * res.expected_dropins, "Spots": res.expected_dropins},
        {"Source": "Gap to maximum", "Revenue": res.max_revenue - res.expected_revenue, "Spots": float("nan")},
    ])
    parts["Order"] = range(len(parts))
    order = ["Members", "ClassPass", "Drop-ins", "Gap to maximum"]
    bar = (alt.Chart(parts, height=150, title="Where expected revenue comes from, and the gap to the maximum")
           .mark_bar(height=34, stroke=PAPER, strokeWidth=2, cornerRadius=4)
           .encode(x=alt.X("sum(Revenue):Q", title=None, axis=alt.Axis(format="$,.0f"),
                           scale=alt.Scale(domain=[0, res.max_revenue])),
                   color=alt.Color("Source:N", sort=order, title=None,
                                   scale=alt.Scale(domain=order, range=[SERIES["Members"], SERIES["ClassPass"], SERIES["Drop-ins"], GAP])),
                   order=alt.Order("Order:Q"),
                   tooltip=[alt.Tooltip("Source:N"), alt.Tooltip("Revenue:Q", format="$,.2f"),
                            alt.Tooltip("Spots:Q", title="Expected spots", format=".1f")]))
    show_chart(bar)

    # ------------------------------------------------------------------ revenue by member limit
    c1, c2 = st.columns([3, 2], gap="large")
    with c1:
        curve = pd.DataFrame({"Member limit": range(CAPACITY + 1), "Expected revenue": res.revenue_by_limit,
                              "Members": res.members_by_limit, "ClassPass": res.classpass_by_limit, "Drop-ins": res.dropins_by_limit})
        lo = curve["Expected revenue"].min()
        hover = alt.selection_point(fields=["Member limit"], nearest=True, on="mouseover", clear="mouseout", empty=False)
        base = alt.Chart(curve, height=300, title="Expected revenue at every member limit").encode(
            x=alt.X("Member limit:Q", title="Stop member bookings at (members)", scale=alt.Scale(domain=[0, CAPACITY])),
            y=alt.Y("Expected revenue:Q", title="Expected revenue per class ($)", axis=alt.Axis(format="$,.0f"),
                    scale=alt.Scale(domain=[max(0, lo - 0.05 * abs(lo)), res.max_revenue * 1.02])))
        line = base.mark_line(color=INK, strokeWidth=2)
        best = base.transform_filter(alt.datum["Member limit"] == res.member_limit).mark_point(
            filled=True, size=110, color=SERIES["Drop-ins"], stroke=PAPER, strokeWidth=2)
        label = base.transform_filter(alt.datum["Member limit"] == res.member_limit).mark_text(
            align="right", dx=-10, dy=-12, color=INK, fontSize=12, fontWeight=600).encode(
            text=alt.value(f"Best: {res.member_limit} members · ${res.expected_revenue:,.0f}"))
        maxline = alt.Chart(pd.DataFrame({"y": [res.max_revenue]})).mark_rule(color=MUTED, strokeDash=[4, 4]).encode(y="y:Q")
        maxlabel = alt.Chart(pd.DataFrame({"y": [res.max_revenue], "x": [0]})).mark_text(
            align="left", dy=-7, color=MUTED, fontSize=11).encode(x="x:Q", y="y:Q", text=alt.value("Maximum"))
        rule = alt.Chart(curve).mark_rule(color=MUTED).encode(
            x="Member limit:Q",
            opacity=alt.condition(hover, alt.value(1), alt.value(0)),
            tooltip=[alt.Tooltip("Member limit:Q"), alt.Tooltip("Expected revenue:Q", format="$,.2f"),
                     alt.Tooltip("Members:Q", title="Expected members", format=".1f"),
                     alt.Tooltip("ClassPass:Q", title="Expected ClassPass", format=".1f"),
                     alt.Tooltip("Drop-ins:Q", title="Expected drop-ins", format=".1f")]).add_params(hover)
        base_pt = base.transform_filter(alt.datum["Member limit"] == CAPACITY).mark_point(
            filled=True, size=90, color=MUTED, stroke=PAPER, strokeWidth=2)
        base_lbl = base.transform_filter(alt.datum["Member limit"] == CAPACITY).mark_text(
            align="right", dx=-8, dy=16, color=MUTED, fontSize=11).encode(
            text=alt.value(f"Baseline (no member limit) · ${baseline:,.0f}"))
        layers = line + maxline + maxlabel + rule + best + label
        if res.member_limit < CAPACITY:
            layers = layers + base_pt + base_lbl
        show_chart(layers)
        st.markdown(f'<div class="jb-note">Each spot held back from members gives up the {money(prices["member"])} a member pays, '
                    f'for a chance at {money(r_D)} from a {"Happy Hour " if hh else ""}drop-in or {money(prices["classpass"])} from ClassPass. '
                    'Holding spots back helps until that chance falls too low. The peak is the recommended member limit.</div>',
                    unsafe_allow_html=True)

    with c2:
        st.markdown("#### Why stop ClassPass at this number?")
        y = res.classpass_protect
        st.markdown(f'<div class="jb-note">Counting the open spots from the drop-ins\' side, a spot is kept for drop-ins when '
                    f'the {money(r_D)} {"Happy Hour " if hh else ""}drop-in price × the chance a drop-in fills it is more than the '
                    f'{money(prices["classpass"])} ClassPass payout.</div>',
                    unsafe_allow_html=True)
        spots = pd.DataFrame(res.spot_table)
        window = spots[(spots.spot >= max(1, y - 2)) & (spots.spot <= min(CAPACITY, y + 2))].copy()
        window["Decision"] = window.keep.map({True: "Keep", False: "To ClassPass"})
        view = window.rename(columns={"spot": "Spot", "chance_dropins_fill": "Drop-in chance",
                                      "expected_dropin_revenue": "Drop-in value"})[
            ["Spot", "Drop-in chance", "Drop-in value", "Decision"]]
        show_table(view.style.format({"Drop-in chance": "{:.0%}", "Drop-in value": "${:,.2f}"})
                   .apply(lambda r: [f"background-color: {'#F3E7DD' if r.Spot == y else ''}"] * len(r), axis=1),
                   hide_index=True)
        if y >= 1:
            last = spots.iloc[y - 1]
            nxt = spots.iloc[y] if y < CAPACITY else None
            txt = f"Spot {y} is worth ${last.expected_dropin_revenue:,.2f} from a drop-in, so it is kept."
            if nxt is not None:
                txt += (f" Spot {y + 1} is worth only ${nxt.expected_dropin_revenue:,.2f}, less than the "
                        f"{money(prices['classpass'])} ClassPass payout, so it is released.")
        else:
            txt = (f"No spots are kept: even the first spot is worth less from a drop-in than the "
                   f"{money(prices['classpass'])} ClassPass payout, so ClassPass can book any available spot.")
        st.markdown(f'<div class="jb-note">{txt}</div>', unsafe_allow_html=True)

    st.write("")

    with st.expander("How the model works"):
        st.markdown(f"""
- **Demand:** for each class, the mean and standard deviation of members, ClassPass and drop-in demand come from the demand data
  (booking-system export). Demand is normally distributed. Classes with high drop-in demand also have high ClassPass demand, which the data reflects directly.
- **ClassPass rule:** a spot is kept for drop-ins when the drop-in price × the chance a drop-in fills it is more than the ClassPass payout.
- **Member rule:** the app calculates expected revenue for every member limit from 0 to {CAPACITY} and picks the highest.
- **Maximum revenue:** all {CAPACITY} spots sold at the drop-in price.
- **Baseline:** expected revenue if all member demand is booked first (no member limit), with the same ClassPass rule.
  The difference from the recommended rules is what the member limit adds. It is a reference point, not Jaybird's current revenue.
- **Assumption:** expected revenue assumes members book first, then ClassPass, then drop-ins. If drop-ins book earlier, they take spots
  ClassPass would have had, so actual revenue would be the same or higher.
""")

    st.markdown('<div class="jb-note" style="margin-top:1.5rem">Built for the MMA 830 Pricing Analytics project (Smith School of Business, Queen\'s University). '
                'Demand values are placeholders until Jaybird booking data is loaded.</div>', unsafe_allow_html=True)
