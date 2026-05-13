import os
import streamlit as st
import pandas as pd
import plotly.express as px
from streamlit_autorefresh import st_autorefresh
from chatbot import process_query
from auth_portal import ROLE_PERMISSIONS, initialize_session, logout, show_login_portal


def format_inr(n):
    """Format a number using the Indian numbering system (e.g. 1,00,000)."""
    n = int(round(n))
    negative = n < 0
    n = abs(n)
    s = str(n)
    if len(s) <= 3:
        result = s
    else:
        last3 = s[-3:]
        rest = s[:-3]
        parts = []
        while len(rest) > 2:
            parts.append(rest[-2:])
            rest = rest[:-2]
        if rest:
            parts.append(rest)
        parts.reverse()
        result = ','.join(parts) + ',' + last3
    return ('-' if negative else '') + result
 

@st.cache_data

def load_data(file_path, file_mtime):
    df = pd.read_csv(file_path)
    df["Start_Date"] = pd.to_datetime(df["Start_Date"])
    df["End_Date"] = pd.to_datetime(df["End_Date"])

    if "State" not in df.columns and "District" in df.columns:
        df["State"] = df["District"]

    def map_zone(district):
        district = str(district).strip().lower()
        if "north" in district or district == "rohini":
            return "North Zone"
        if "south" in district or district == "saket":
            return "South Zone"
        if "east" in district:
            return "East Zone"
        if "west" in district or district == "dwarka":
            return "West Zone"
        if "central" in district or district == "karol bagh":
            return "Central Zone"
        return "Other Zone"

    df["Zone"] = df["District"].apply(map_zone)
    df["Budget_Utilization_%"] = (df["Budget_Used"] / df["Budget_Allocated"]) * 100
    df["Profit"] = df["Revenue_Generated"] - df["Budget_Used"]
    df["ROI_%"] = (df["Profit"] / df["Budget_Used"]) * 100
    df["Project_Duration"] = (df["End_Date"] - df["Start_Date"]).dt.days
    return df


# -----------------------------
# PAGE CONFIG
# -----------------------------
st.set_page_config(page_title="Bharat ICT Dashboard", layout="wide")
st_autorefresh(interval=3000, key="dashboard_autorefresh")
initialize_session()

# -----------------------------
# CUSTOM CSS (Professional UI)
# -----------------------------
st.markdown("""
    <style>
        .main {
            background-color: #f5f7fa;
        }
        .block-container {
            padding-top: 2rem;
        }
        h1 {
            color: #0a3d62;
        }
    </style>
""", unsafe_allow_html=True)

if not st.session_state.logged_in:
    show_login_portal()

current_user = st.session_state.user
user_role = current_user["role"]
data_file = "data/telecom_projects.csv"
df = load_data(data_file, os.path.getmtime(data_file))

# -----------------------------
# TITLE SECTION
# -----------------------------
st.title("BHARAT ICT DATA ANALYTICS & BUSINESS INTELLIGENCE DASHBOARD")
st.markdown("### Strategic Monitoring & Performance Intelligence System")
st.caption(
    f"Logged in as: {current_user['name']} • {user_role} • Live refresh enabled • Last update: {pd.Timestamp.now().strftime('%I:%M:%S %p')}"
)
st.markdown("---")

# -----------------------------
# SIDEBAR ACCESS PANEL
# -----------------------------
st.sidebar.header("Access Panel")
st.sidebar.success(f"User ID: {current_user['user_id']}")
st.sidebar.write(f"Role: {user_role}")
st.sidebar.info(ROLE_PERMISSIONS[user_role])

if st.sidebar.button("Logout", width='stretch'):
    logout()

# -----------------------------
# SIDEBAR FILTERS
# -----------------------------
st.sidebar.header("Filters")

zone_filter = st.sidebar.multiselect(
    "Select Zone",
    sorted(df["Zone"].unique()),
    default=sorted(df["Zone"].unique())
)

available_districts = sorted(df[df["Zone"].isin(zone_filter)]["District"].unique())

district_filter = st.sidebar.multiselect(
    "Select District",
    available_districts,
    default=available_districts
)

status_filter = st.sidebar.multiselect(
    "Select Project Status",
    sorted(df["Status"].unique()),
    default=sorted(df["Status"].unique())
)

client_type_filter = st.sidebar.multiselect(
    "Select Client Type",
    sorted(df["Client_Type"].unique()),
    default=sorted(df["Client_Type"].unique())
)

project_type_filter = st.sidebar.multiselect(
    "Select Project Type",
    sorted(df["Project_Type"].unique()),
    default=sorted(df["Project_Type"].unique())
)

st.sidebar.markdown("**Budget Allocated Range (₹)**")
budget_min = int(df["Budget_Allocated"].min())
budget_max = int(df["Budget_Allocated"].max())
budget_range = st.sidebar.slider(
    "Budget Range",
    min_value=budget_min,
    max_value=budget_max,
    value=(budget_min, budget_max),
    step=100000,
    format="₹%d"
)

team_min = int(df["Team_Size"].min())
team_max = int(df["Team_Size"].max())
team_range = st.sidebar.slider(
    "Team Size",
    min_value=team_min,
    max_value=team_max,
    value=(team_min, team_max)
)

st.sidebar.markdown("**Start Date Range**")
date_min = df["Start_Date"].min().date()
date_max = df["Start_Date"].max().date()
start_date_from = st.sidebar.date_input("From", value=date_min, min_value=date_min, max_value=date_max)
start_date_to = st.sidebar.date_input("To", value=date_max, min_value=date_min, max_value=date_max)

filtered_df = df[
    (df["Zone"].isin(zone_filter)) &
    (df["District"].isin(district_filter)) &
    (df["Status"].isin(status_filter)) &
    (df["Client_Type"].isin(client_type_filter)) &
    (df["Project_Type"].isin(project_type_filter)) &
    (df["Budget_Allocated"] >= budget_range[0]) &
    (df["Budget_Allocated"] <= budget_range[1]) &
    (df["Team_Size"] >= team_range[0]) &
    (df["Team_Size"] <= team_range[1]) &
    (df["Start_Date"].dt.date >= start_date_from) &
    (df["Start_Date"].dt.date <= start_date_to)
]

alert_projects = filtered_df[
    (filtered_df["Profit"] < 0) | (filtered_df["ROI_%"] < 5)
].copy()
loss_projects = alert_projects[alert_projects["Profit"] < 0]
low_roi_projects = alert_projects[alert_projects["ROI_%"] < 5]
delayed_projects_df = filtered_df[filtered_df["Status"] == "Delayed"].copy()

total_alerts = alert_projects.shape[0] + delayed_projects_df.shape[0]
if total_alerts == 0:
    st.sidebar.success("No financial alerts")
else:
    st.sidebar.warning(f"Financial Alerts: {total_alerts}")

# -----------------------------
# KPI SECTION
# -----------------------------
total_projects = filtered_df.shape[0]
total_budget = filtered_df["Budget_Allocated"].sum()
total_revenue = filtered_df["Revenue_Generated"].sum()
avg_roi = filtered_df["ROI_%"].mean()
completion_rate = (
    filtered_df[filtered_df["Status"] == "Completed"].shape[0]
    / total_projects * 100
) if total_projects > 0 else 0

st.markdown("## Key Performance Indicators")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Projects", total_projects)
if user_role == "Employee":
    col2.metric("Total Budget Allocated", "🔒 Restricted")
    col3.metric("Total Revenue Generated", "🔒 Restricted")
    col4.metric("Average ROI (%)", "🔒 Restricted")
else:
    col2.metric("Total Budget Allocated", f"₹ {format_inr(total_budget)}")
    col3.metric("Total Revenue Generated", f"₹ {format_inr(total_revenue)}")
    col4.metric("Average ROI (%)", f"{avg_roi:.2f}%")

st.markdown("---")

# -----------------------------
# ALERT CENTER
# -----------------------------
st.markdown("## Project Alert Center")

if user_role == "Employee":
    st.error("🔒 Restricted — Financial alerts and loss/ROI data are not accessible for the **Employee** role.")
else:
    alert_col1, alert_col2, alert_col3, alert_col4 = st.columns(4)
    alert_col1.metric("Projects in Loss", int(loss_projects.shape[0]))
    alert_col2.metric("ROI Below 5%", int(low_roi_projects.shape[0]))
    alert_col3.metric("Delayed Projects", int(delayed_projects_df.shape[0]))
    alert_col4.metric("Total Alerts", int(alert_projects.shape[0]) + int(delayed_projects_df.shape[0]))

    if alert_projects.empty and delayed_projects_df.empty:
        st.success("No critical financial issues detected in the selected projects.")
    else:
        if not loss_projects.empty:
            st.error(f"{loss_projects.shape[0]} project(s) are currently running at a loss.")
        if not low_roi_projects.empty:
            st.warning(f"{low_roi_projects.shape[0]} project(s) have ROI below 5%.")
        if not delayed_projects_df.empty:
            st.warning(f"{delayed_projects_df.shape[0]} project(s) are delayed.")

        if not alert_projects.empty:
            st.markdown("**Financial Alerts (Loss / Low ROI)**")
            alert_view = alert_projects[[
                "Project_ID", "Project_Name", "Zone", "District", "Status",
                "Profit", "ROI_%", "Budget_Used", "Revenue_Generated"
            ]].sort_values(by=["Profit", "ROI_%"])
            st.dataframe(alert_view, width='stretch')

        if not delayed_projects_df.empty:
            st.markdown("**Delayed Projects**")
            delay_cols = [c for c in ["Project_ID", "Project_Name", "Zone", "District", "Delay_Days", "Status"] if c in delayed_projects_df.columns]
            st.dataframe(delayed_projects_df[delay_cols].sort_values("Delay_Days", ascending=False), width='stretch')

st.markdown("---")

# -----------------------------
# DURATION & RISK ANALYSIS
# -----------------------------
st.markdown("## Project Duration & Risk Insights")

avg_duration = filtered_df["Project_Duration"].mean()
max_duration = filtered_df["Project_Duration"].max()
delayed_projects = filtered_df[filtered_df["Status"] == "Delayed"].shape[0]

col1, col2, col3 = st.columns(3)
col1.metric("Average Duration (Days)", int(avg_duration) if not pd.isna(avg_duration) else 0)
col2.metric("Longest Project (Days)", int(max_duration) if not pd.isna(max_duration) else 0)
col3.metric("Delayed Projects", delayed_projects)

st.markdown("---")

# -----------------------------
# VISUALIZATIONS
# -----------------------------
st.markdown("## Financial Performance")

if user_role == "Employee":
    st.error("🔒 Restricted — Financial performance charts (ROI, Budget, Revenue) are not accessible for the **Employee** role.")
else:
    roi_chart_df = filtered_df.sort_values("ROI_%", ascending=True)
    fig1 = px.bar(
        roi_chart_df,
        x="Project_Name",
        y="ROI_%",
        color="Status",
        title="ROI % by Project"
    )
    fig1.add_hline(y=5, line_dash="dash", line_color="orange", annotation_text="Alert threshold: 5%")
    st.plotly_chart(fig1, width='stretch')

    fig2 = px.pie(
        filtered_df,
        names="District",
        values="Budget_Allocated",
        title="Budget Allocation by District"
    )
    st.plotly_chart(fig2, width='stretch')

    scatter_df = filtered_df.copy()
    scatter_df["Bubble_Size"] = scatter_df["ROI_%"].abs().clip(lower=1)
    scatter_df["Budget_Lakhs"] = scatter_df["Budget_Allocated"] / 1e5
    scatter_df["Revenue_Lakhs"] = scatter_df["Revenue_Generated"] / 1e5

    fig3 = px.scatter(
        scatter_df,
        x="Budget_Lakhs",
        y="Revenue_Lakhs",
        color="Status",
        size="Bubble_Size",
        hover_name="Project_Name",
        hover_data={"ROI_%": ":.2f", "Bubble_Size": False, "Budget_Lakhs": ":.1f", "Revenue_Lakhs": ":.1f"},
        title="Budget vs Revenue Analysis",
        labels={"Budget_Lakhs": "Budget Allocated (₹ Lakhs)", "Revenue_Lakhs": "Revenue Generated (₹ Lakhs)"}
    )
    fig3.update_layout(
        xaxis=dict(tickprefix="₹ ", ticksuffix=" L", tickformat=".0f"),
        yaxis=dict(tickprefix="₹ ", ticksuffix=" L", tickformat=".0f"),
    )
    st.plotly_chart(fig3, width='stretch')

st.markdown("---")

# -----------------------------
# ROLE-BASED DATA ACCESS
# -----------------------------
if user_role == "Super Admin":
    st.markdown("## Super Admin Record Access")
    st.dataframe(filtered_df, width='stretch')
    st.download_button(
        "Download Filtered Records",
        data=filtered_df.to_csv(index=False).encode("utf-8"),
        file_name="telecom_projects_filtered.csv",
        mime="text/csv",
        width='stretch',
    )
elif user_role == "Project Manager":
    st.markdown("## Project Manager Operational View")
    manager_view = filtered_df[[
        "Project_ID", "Project_Name", "Zone", "District", "Status", "Team_Size",
        "Delay_Days", "Budget_Allocated", "Budget_Used", "ROI_%"
    ]]
    st.dataframe(manager_view, width='stretch')
else:
    st.markdown("## Employee View")
    st.error("🔒 Restricted Access — You are logged in as **Employee**. The following data is hidden from your role: financial figures, budgets, ROI, profit, and downloads.")
    st.info("Showing project status and general information only.")
    employee_view = filtered_df[["Project_Name", "Zone", "District", "Status"]].sort_values("Project_Name")
    st.dataframe(employee_view, width='stretch')

st.markdown("---")

# -----------------------------
# EXECUTIVE SUMMARY
# -----------------------------
st.markdown("## Executive Summary")
st.write(f"""
• The organization is currently managing **{total_projects} telecom infrastructure projects** across selected regions.

• Total capital investment stands at **₹ {format_inr(total_budget)}**, generating **₹ {format_inr(total_revenue)}** in revenue.

• The portfolio delivers an average **ROI of {avg_roi:.2f}%**, indicating financial efficiency.

• Project completion efficiency stands at **{completion_rate:.1f}%**, with **{delayed_projects} projects facing delays**.

• Strategic focus should be directed toward high-duration and delayed projects to optimize performance.
""")

st.markdown("---")

# -----------------------------
# CHATBOT SECTION
# -----------------------------
if user_role in ["Super Admin", "Project Manager"]:
    st.markdown("## AI Project Assistant")
    chat_col1, chat_col2 = st.columns([1, 1])

    with chat_col2:
        st.markdown("### Ask me about your projects")

        for message in st.session_state.chat_history:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        user_input = st.chat_input("Ask about delayed projects, budget, ROI, etc...")

        if user_input:
            st.session_state.chat_history.append({"role": "user", "content": user_input})
            response = process_query(user_input, filtered_df)
            st.session_state.chat_history.append({"role": "assistant", "content": response})
            st.rerun()
else:
    st.markdown("## AI Project Assistant")
    st.error("🔒 Restricted — The AI Project Assistant is not available for the **Employee** role.")
