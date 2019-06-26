from flask import Flask, render_template, request, redirect
import requests
import pandas as pd
from pandas.io.json import json_normalize
from bokeh.plotting import figure, show
from bokeh.models import ColumnDataSource
from bokeh.models.tools import HoverTool
from bokeh.layouts import gridplot
from bokeh.embed import components
import numpy as np
import os

app = Flask(__name__)

# Global set-ups for free NBA api
XRapid_api_key = os.environ.get('Rapid_API_KEY')
XRapid_api_host = "free-nba.p.rapidapi.com"
free_nba_api_endpoint = "https://free-nba.p.rapidapi.com/games"

# Collect all data in a loop
def _get_response(params, page=None):
    if page:
        params.update({'page': page})
        
    res = requests.get(free_nba_api_endpoint, 
                       params=params,
                       headers={
                           "X-RapidAPI-Host": XRapid_api_host,
                           "X-RapidAPI-Key": XRapid_api_key
                       }
                      )
    content_dict = res.json()
    if content_dict['meta']['next_page']:
        next_page = content_dict['meta']['next_page']
    else:
        next_page = False
    return content_dict['data'], next_page

# Convert data into pandas dataframe
def nba_data_processing(nba_data_dict):
    df = pd.DataFrame.from_dict(json_normalize(nba_data_dict, sep='_'), orient='columns')
    return df

# Get scores data for a single season
def get_data(season=2018):
    results = []
    params = {'seasons[]': season, 'per_page': 100}

    res, next_page = _get_response(params)
    results.extend(res)

    while next_page:
        res, next_page = _get_response(params, page=next_page)
        results.extend(res)
	
    df = nba_data_processing(results)

    # Reformat date
    df['date'] = df.apply(lambda x: x.date.replace('T00:00:00.000Z', ''), axis=1)

    return df

# Create bokeh plots
def create_plot(df, season):
    source_east_both = ColumnDataSource(df[(df.home_team_conference == 'East') & (df.visitor_team_conference == 'East')])
    source_west_both = ColumnDataSource(df[(df.home_team_conference == 'West') & (df.visitor_team_conference == 'West')])
    source_west_at_east = ColumnDataSource(df[(df.home_team_conference == 'East') & (df.visitor_team_conference == 'West')])
    source_east_at_west = ColumnDataSource(df[(df.home_team_conference == 'East') & (df.visitor_team_conference == 'West')])

    TOOLS="pan,wheel_zoom,box_select,lasso_select,reset"
    p = figure(tools=TOOLS, plot_width=600, plot_height=600, min_border=10, min_border_left=50, toolbar_location="above")

    p.background_fill_color = "#fafafa"


    p.scatter(x='home_team_score', y='visitor_team_score',
         	source=source_east_both,
         	size=8, alpha=0.6, color='blue', legend="Both East teams")
    p.scatter(x='home_team_score', y='visitor_team_score',
         	source=source_west_both,
         	size=8, alpha=0.7, color='red', legend="Both West teams")
    p.scatter(x='home_team_score', y='visitor_team_score',
         	source=source_west_at_east,
         	size=8, alpha=0.7, color='green', legend="West @ East")
    p.scatter(x='home_team_score', y='visitor_team_score',
         	source=source_east_at_west,
         	size=8, alpha=0.7, color='yellow', legend="East @ West")

    p.legend.location = "top_left"
    p.legend.click_policy="hide"

    p.title.text = 'All team scores in Season '+str(season)
    p.xaxis.axis_label = 'Home team score'
    p.yaxis.axis_label = 'Visitor team score'

    hover = HoverTool()
    hover.tooltips=[
    	('Home Team', '@home_team_full_name'),
    	('Home Team Score', '@home_team_score'),
    	('Visitor Team', '@visitor_team_full_name'),
    	('Visitor Team Score', '@visitor_team_score'),
    	('Date', '@date')
		]

    p.add_tools(hover)

    return p


@app.route('/')
def index():
    current_season = request.args.get("Season")
    if current_season == None:
        return render_template('index.html',
		    seasons=list(range(1979, 2019))
		    )
        current_season = 2018

    # Collect data
    data_frame = get_data(current_season)

    # Create plots
    plot = create_plot(data_frame, current_season)

    # Embed plot into HTML via Flask Render
    script, div = components(plot)

    return render_template('index.html', script=script, div=div,
		current_season=current_season, 
		seasons=list(range(1979, 2019))
		)

@app.route('/about')
def about():
    return render_template('about.html')

if __name__ == '__main__':
    app.run(port=33507)
