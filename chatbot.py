"""
Chatbot Module for Bharat ICT Dashboard
Handles natural language project queries with role-friendly summaries.
"""

import re


def _format_inr(n):
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


def _extract_top_n(text, default=5):
    match = re.search(r"top\s+(\d+)|bottom\s+(\d+)", text)
    if match:
        for group in match.groups():
            if group:
                return max(1, int(group))
    return default


def _find_match(text, values):
    text = text.lower()
    for value in sorted(values, key=len, reverse=True):
        if str(value).lower() in text:
            return value
    return None


def _format_table(title, df):
    if df.empty:
        return f"{title}\n\nNo matching records found."
    return f"{title}\n\n{df.to_string(index=False)}"


def get_delayed_projects(df, limit=5):
    delayed = df[df["Status"] == "Delayed"].nlargest(limit, "Delay_Days")
    cols = [col for col in ["Project_Name", "District", "Delay_Days", "Status"] if col in delayed.columns]
    return delayed[cols]


def get_budget_overrun_projects(df, limit=5):
    df_copy = df.copy()
    df_copy["Budget_Overrun"] = df_copy["Budget_Used"] - df_copy["Budget_Allocated"]
    overrun = df_copy[df_copy["Budget_Overrun"] > 0].sort_values("Budget_Overrun", ascending=False)
    cols = ["Project_Name", "District", "Budget_Allocated", "Budget_Used", "Budget_Overrun", "Status"]
    return overrun[[c for c in cols if c in overrun.columns]].head(limit)


def get_highest_profit_projects(df, top_n=5):
    profitable = df.nlargest(top_n, "Profit")
    cols = ["Project_Name", "District", "Profit", "Revenue_Generated", "Budget_Used", "Status"]
    return profitable[[c for c in cols if c in profitable.columns]]


def get_high_roi_projects(df, top_n=5):
    top_roi = df.nlargest(top_n, "ROI_%")
    cols = ["Project_Name", "District", "ROI_%", "Profit", "Status"]
    return top_roi[[c for c in cols if c in top_roi.columns]]


def get_low_performers(df, top_n=5):
    low_performers = df.nsmallest(top_n, "ROI_%")
    cols = ["Project_Name", "District", "ROI_%", "Status", "Profit"]
    return low_performers[[c for c in cols if c in low_performers.columns]]


def get_alert_projects(df, top_n=10):
    alert_df = df[(df["Profit"] < 0) | (df["ROI_%"] < 5)].copy()
    cols = ["Project_Name", "District", "ROI_%", "Profit", "Status"]
    return alert_df.sort_values(by=["Profit", "ROI_%"])[[c for c in cols if c in alert_df.columns]].head(top_n)


def get_revenue_analysis(df):
    if df.empty:
        return "No data available for revenue analysis."
    highest = df.loc[df["Revenue_Generated"].idxmax()]
    lowest = df.loc[df["Revenue_Generated"].idxmin()]
    return f"""Revenue Analysis:
• Highest Revenue Project: {highest['Project_Name']} (₹ {_format_inr(highest['Revenue_Generated'])})
• Lowest Revenue Project: {lowest['Project_Name']} (₹ {_format_inr(lowest['Revenue_Generated'])})
• Average Revenue: ₹ {_format_inr(df['Revenue_Generated'].mean())}
• Total Revenue: ₹ {_format_inr(df['Revenue_Generated'].sum())}"""


def get_team_size_analysis(df):
    return f"""Team Size Analysis:
• Largest Team: {df['Team_Size'].max()} members
• Smallest Team: {df['Team_Size'].min()} members
• Average Team Size: {df['Team_Size'].mean():.1f} members
• Total Team Members: {df['Team_Size'].sum()}"""


def get_portfolio_summary(df, label="Portfolio"):
    return f"""{label} Summary:
• Total Projects: {len(df)}
• Total Budget: ₹ {_format_inr(df['Budget_Allocated'].sum())}
• Total Revenue: ₹ {_format_inr(df['Revenue_Generated'].sum())}
• Average ROI: {df['ROI_%'].mean():.2f}%
• Completed: {len(df[df['Status'] == 'Completed'])}
• Ongoing: {len(df[df['Status'] == 'Ongoing'])}
• Delayed: {len(df[df['Status'] == 'Delayed'])}"""


def process_query(user_input, data):
    """Process natural language queries and return a relevant dashboard answer."""
    if data.empty:
        return "No project data is available right now."

    query = user_input.lower().strip()
    top_n = _extract_top_n(query)

    district_match = _find_match(query, data["District"].dropna().unique()) if "District" in data.columns else None
    zone_match = _find_match(query, data["Zone"].dropna().unique()) if "Zone" in data.columns else None
    state_match = _find_match(query, data["State"].dropna().unique()) if "State" in data.columns else None

    scoped_data = data
    scope_label = "Portfolio"

    if district_match:
        scoped_data = data[data["District"] == district_match]
        scope_label = f"{district_match} District"
    elif zone_match:
        scoped_data = data[data["Zone"] == zone_match]
        scope_label = f"{zone_match}"
    elif state_match:
        scoped_data = data[data["State"] == state_match]
        scope_label = f"{state_match} State"

    if any(word in query for word in ["hello", "hi", "hey"]):
        return "Hello. Ask about ROI, delays, revenue, district summaries, zone summaries, or top projects."

    if any(word in query for word in ["help", "guide", "what can", "options", "example"]):
        return """I can help with:
• Delayed projects
• Budget overruns
• Top or bottom ROI projects
• Profit and revenue analysis
• District or zone summaries
• Team size and portfolio overview
• Financial alerts, losses, and low ROI risks

Examples:
• Show delayed projects in North Zone
• Top 3 ROI projects
• Revenue analysis for Dwarka
• Portfolio summary
• Budget overrun projects
• Show project alerts"""

    if any(word in query for word in ["delay", "delayed", "late", "pending", "overdue", "behind"]):
        result = get_delayed_projects(scoped_data, top_n)
        return _format_table(f"Delayed Projects for {scope_label}:", result)

    if any(word in query for word in ["budget overrun", "budget exceeded", "overspent", "over-budget", "over budget", "budget overflow"]):
        result = get_budget_overrun_projects(scoped_data, top_n)
        if result.empty:
            return f"No budget overruns found for {scope_label}."
        return _format_table(f"Budget Overrun Projects for {scope_label}:", result)

    if any(word in query for word in ["alert", "alerts", "loss", "losses", "risk", "critical"]):
        result = get_alert_projects(scoped_data, top_n)
        if result.empty:
            return f"No alert-worthy projects found for {scope_label}."
        return _format_table(f"Financial Alerts for {scope_label}:", result)

    if any(word in query for word in ["high roi", "best performing", "top performer", "top projects", "best roi", "roi"]):
        result = get_high_roi_projects(scoped_data, top_n)
        return _format_table(f"Top ROI Projects for {scope_label}:", result)

    if any(word in query for word in ["low roi", "low performing", "worst", "underperform", "bottom"]):
        result = get_low_performers(scoped_data, top_n)
        return _format_table(f"Low Performing Projects for {scope_label}:", result)

    if any(word in query for word in ["profit", "profitable", "highest profit", "most profit"]):
        result = get_highest_profit_projects(scoped_data, top_n)
        return _format_table(f"Highest Profit Projects for {scope_label}:", result)

    if any(word in query for word in ["revenue", "income", "sales", "generated"]):
        return get_revenue_analysis(scoped_data)

    if any(word in query for word in ["team", "workforce", "members", "staff", "employees", "size", "people"]):
        return get_team_size_analysis(scoped_data)

    if any(word in query for word in ["summary", "overview", "district", "zone", "location", "area", "how many", "total", "count", "number", "portfolio"]):
        return get_portfolio_summary(scoped_data, scope_label)

    return "I can answer questions about delays, ROI, revenue, profit, district summaries, zone summaries, budget overruns, and team size. Type help for examples."

