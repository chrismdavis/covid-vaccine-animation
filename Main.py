import pandas as pd
from datetime import datetime, date, timedelta
import numpy as np

# Import Data
df_election = pd.read_csv('2020_US_County_Level_Presidential_Results.csv')
df_vax = pd.read_csv("COVID-19_Vaccinations_in_the_United_States_County_Reduced.csv")

# Clean vaccine database
df_vax = df_vax[['Date', 'FIPS', 'Series_Complete_Yes', 'Series_Complete_Pop_Pct']]
df_vax = df_vax.rename(columns={'Series_Complete_Yes': 'Vax_Cnt', 'Series_Complete_Pop_Pct': 'Vax_Rate'})
df_vax.Date = df_vax.Date.apply(lambda x: datetime.strptime(x, '%m/%d/%Y'))

# Add population
df_vax['Pop_Calc'] = round(df_vax.Vax_Cnt / df_vax.Vax_Rate, 0)
df_vax = df_vax.merge(df_vax[['FIPS', 'Pop_Calc']][df_vax.Date == df_vax.Date.max()], how='left', on='FIPS')
df_vax = df_vax.rename(columns={'Pop_Calc_y': 'Population'})
df_vax = df_vax[['Date', 'FIPS', 'Vax_Cnt', 'Vax_Rate', 'Population']]

# Clean election database
df_election = df_election[['county_fips', 'per_gop', 'per_dem']]
df_election = df_election.rename(columns={'county_fips': 'FIPS'})
df_election['Perc_Rep'] = df_election['per_gop'] / (df_election['per_gop'] + df_election['per_dem'])
df_election['Perc_Dem'] = df_election['per_dem'] / (df_election['per_gop'] + df_election['per_dem'])
df_election['FIPS'] = df_election['FIPS'].apply(lambda x: '00000' if pd.isna(x) else str(int(x)).zfill(5))
df_election = df_election[['FIPS', 'Perc_Rep', 'Perc_Dem']]
df_election = df_election.dropna()

# Add voting rate to df_vax
df_vax = df_vax.merge(df_election, how='inner', on='FIPS')
df_vax['Bin'] = round(df_vax.Perc_Dem, 1)
df_vax["Bin"].replace({1: .9, 0: .1}, inplace=True)

# Create grouped df
master_df = df_vax[['Date', 'Bin', 'Vax_Cnt', 'Population']].groupby(by=['Date', 'Bin']).sum().reset_index()
master_df['Vax_Rate'] = master_df['Vax_Cnt'] / master_df['Population']
master_df = master_df[['Date', 'Bin', 'Vax_Rate']]
master_df = master_df.pivot_table(values='Vax_Rate', index='Date', columns='Bin')

# Smooth with moving average
MA_Val = 14
for i in master_df.columns:
    master_df[i] = master_df[i].rolling(MA_Val).mean()
    master_df[i] = master_df[i].rolling(MA_Val).mean()

master_df = master_df.dropna()

# Create animation
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter, FFMpegWriter
import matplotlib.dates as mdates
import matplotlib.colors as mcol
import matplotlib.ticker as mtick
import matplotlib.cm as cm

plt.style.use('dark_background')
plt.rc('font', size=2, )
plt.rc('axes', titlesize=12, titleweight='normal')
plt.rc('axes', labelsize=12, labelweight='bold')
plt.rc('xtick', labelsize=10)
plt.rc('ytick', labelsize=10)
plt.rc('figure', titlesize=24, titleweight='bold')
clr_pick = cm.ScalarMappable(norm=mcol.Normalize(vmin=.1, vmax=.9),
                             cmap=mcol.LinearSegmentedColormap.from_list("Political", ["r", "b"]))
clr_pick.set_array([])

fig, ax = plt.subplots(1, 1, figsize=(6, 6))
plt.subplots_adjust(left=0.1, right=0.99, top=.85, bottom=0.1)
fig.colorbar(clr_pick, orientation='vertical', format=mtick.PercentFormatter(xmax=1, decimals=0),
             label=' \n % of Vote Democratic')
fig.suptitle(' \n Average Covid Vaccination Rates by County Political Demographic')
fig.set_size_inches(14, 10)


def animate(j):
    if j > len(master_df):
        j = len(master_df)

    x = master_df.index[:j].values
    ax.cla()
    ax.set_title(
        "\n * County demographics compiled from 2020 presidential election voting results \n * Vaccination data "
        "source: Centers for Disease Control and Prevention",
        fontsize=9, loc='left')
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%b'))
    ax.yaxis.set_major_formatter(mtick.PercentFormatter())
    ax.set_xlim([date(2021, 1, 1), x.max()])
    ax.set_yticks([0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70])
    ax.set_ylim([0, 70])
    ax.set_ylabel("Full Vaccination Rate")
    ax.set_xlabel("Month (2021)")
    ax.grid()
    for i in master_df.columns:
        ax.plot(x, master_df[i][:j].values, label=str(i), color=clr_pick.to_rgba(i), linewidth=4,
                solid_capstyle='round')


anim = FuncAnimation(fig, animate, frames=range(2, len(master_df) + 10), interval=1, blit=False)
fig.show()

anim.save('T3.gif', writer='imagemagick')
