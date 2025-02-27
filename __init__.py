import logging
from eventmanager import Evt
import matplotlib.pyplot as plt
import matplotlib.lines as mlines
import matplotlib.ticker as mticker
import pandas as pd
import seaborn as sns
from flask import templating
from flask.blueprints import Blueprint




class ResultsPlot:
    def __init__(self, rhapi):
        self.logger = logging.getLogger(__name__)
        self._rhapi = rhapi

    def init_plugin(self, args):
        self.logger.info("Results Plot Plugin initialised")

    def update_plot(self, args):
        raceclass = self._rhapi.db.raceclasses
        raceclass_results = self._rhapi.db.raceclass_results(raceclass[0])

        if raceclass_results is not None:
            self.logger.info("rplots - creating plot")
            pilot_race_order = [i['pilot_id'] for i in raceclass_results['by_consecutives']]
            consecutive_time = [i['consecutives'] for i in raceclass_results['by_consecutives']]
            #consecutive_time_nlaps = [i['consecutives_base'] for i in raceclass_results['by_consecutives']]
            consecutive_time_round = [i['consecutives_source']['heat'] for i in raceclass_results['by_consecutives']]
            consecutive_time_lap_start = [i['consecutive_lap_start'] for i in raceclass_results['by_consecutives']]
            # self.logger.info(consecutive_time_round)
            # self.logger.info(consecutive_time_lap_start)
            pilots = self._rhapi.db.pilots
            #Create pilot information lists
            pilot_ids = []
            pilot_names = []
            pilot_colours = []

            for i in range(len(pilots)):
                pilot_ids.append(pilots[i].id)
                pilot_names.append(pilots[i].callsign)
                pilot_colours.append(pilots[i].color)

            races = self._rhapi.db.pilotruns

            #Create list of pilot runs for each pilot
            pilot_list = []
            for i in range(len(pilots)):
                pilot_list.append([])
            for r in range(len(races)):
                if races[r].pilot_id != 0:
                    pilot_list[pilot_ids.index(races[r].pilot_id)].append(races[r].id)

            results_df=pd.DataFrame(columns=["Pilot","Lap Time", "Round", "Lap", "Best Q"])
            for i in range(len(pilot_list)):
                for j,jj in enumerate(pilot_list[i]):
                    laps = self._rhapi.db.laps_by_pilotrun(pilot_list[i][j])
                    heats = [lap.race_id for lap in laps]
                    this_pilot = laps[0].pilot_id
                    #remove deleted laps
                    temp_laps = [lap.lap_time_formatted for lap in laps if lap.deleted == 0]
                    #ignore the first lap time = holeshot and reformat string into seconds
                    for k in range(len(temp_laps)):
                        time_in_seconds = (float(temp_laps[k].split(":")[0] * 60) +
                                            float(temp_laps[k].split(":")[1]))
                        if heats[0] == consecutive_time_round[i]:
                            if k >= consecutive_time_lap_start[i] and k < (consecutive_time_lap_start[i] + 3):
                                qlap = int(1)
                            else:
                                qlap = int(0)
                        else:
                            qlap=int(0)
                        results_df.loc[len(results_df)]={"Pilot" : str(this_pilot),"Lap Time" :time_in_seconds,
                                                         "Round" : int(j),
                                                         "Lap": int(k),
                                                         "Best Q":qlap}
            #self.logger.info(results_df)

            #self.logger.info(pilot_colours)
            results_df['Pilot'] = results_df['Pilot'].astype(str)
            fig, ax = plt.subplots(figsize=(10, 7))

            medianprops = dict(color="black",linewidth=1.5)
            #Box Plot
            sns.boxplot(data=results_df[results_df["Lap"] > 0], x="Lap Time", y="Pilot", hue="Pilot",palette=pilot_colours,
                          orient="h", ax=ax,
                          legend=False,
                          medianprops=medianprops,
                          order=pilot_race_order)
            #Raw Data
            sns.stripplot(data=results_df[results_df["Lap"] > 0], x="Lap Time", y="Pilot", hue="Pilot",palette=pilot_colours,
                          ax=ax, size=5, jitter=True,
                          linewidth = 1,
                          edgecolor="black",
                          alpha=0.6,
                          legend=False,
                          dodge=False,
                          order=pilot_race_order)
            #Qualifying Laps
            sns.stripplot(data=results_df[results_df["Best Q"] == 1], x="Lap Time", y="Pilot", hue="Pilot",
                          jitter=False, size=6, alpha=1, linewidth=0.8, palette='dark:#FFFF00', edgecolor="black",
                          ax=ax,
                          legend=False,
                          dodge=False,
                          order=pilot_race_order)
            #Hole Shots
            sns.stripplot(data=results_df[results_df["Lap"] == 0], x="Lap Time", y="Pilot", hue="Pilot",
                          jitter=False, size=3, alpha=1, linewidth=0.8, palette='dark:pink', edgecolor="black",
                          marker="^",
                          ax=ax,
                          legend=False,
                          dodge=False)

            ax.set_xlabel('Lap Time (seconds)', color="black")
            ax.set_yticks(range(len(results_df['Pilot'].unique())))
            ylabels=[]
            for i in range(len(ax.get_yticks())):
                ylabels.append(f"{pilot_names[pilot_ids.index(pilot_race_order[i])]} \n"
                               f"{consecutive_time[i]}s")
            ax.set_yticklabels(ylabels)
            # ticks_loc = ax.get_yticks().tolist()
            # ax.yaxis.set_major_locator(mticker.FixedLocator(ticks_loc))

            strip_legend1 = mlines.Line2D([], [], color="none", mec="black", marker="o", linestyle="None",
                                          markersize=6, label="Raw Lap Times")
            strip_legend2 = mlines.Line2D([], [], color="#FFFF00", marker="o", linestyle="None", mec="black",
                                          markersize=6, label="Fastest 3 Consecutive Lap Times")
            strip_legend3 = mlines.Line2D([], [], color="pink", marker="^", linestyle="None",
                                          markersize=4, label="Holeshots")
            plt.legend(handles=[strip_legend3,strip_legend1,strip_legend2], loc="upper right", fontsize=8, frameon=True)


            min_x, max_x = results_df["Lap Time"].min(), results_df["Lap Time"].max()
            increment=2
            ax.set_xticks(range(int(min_x // increment) * increment, int(max_x // increment) * increment + (2*increment), increment))  # Ticks every increment
            ax.xaxis.grid(True, linestyle='--', alpha=0.4, color="gray")
            plt.savefig("plugins/rh_rplots/static/boxplot.png", dpi=300, bbox_inches='tight')

            self.logger.info("Plot Done")
        else:
            self.logger.info("No results to plot")


def initialize(rhapi):
    results_plot = ResultsPlot(rhapi)
    rhapi.events.on(Evt.STARTUP, results_plot.init_plugin)
    rhapi.events.on(Evt.STARTUP, results_plot.update_plot)
    rhapi.events.on(Evt.LAPS_SAVE, results_plot.update_plot)
    rhapi.events.on(Evt.LAPS_RESAVE, results_plot.update_plot)
    rhapi.ui.register_panel("Lap Time Stats", "Lap Time Stats", "format")
    rhapi.ui.register_quickbutton("Lap Time Stats", "rplots_update", "Manual Plot Update", results_plot.update_plot)

    bp = Blueprint(
        'results_plot',
        __name__,
        template_folder='pages',
        static_folder='static',
        static_url_path='/rh_rplots/static'
    )

    @bp.route('/results_plot')
    def results_plot_homePage():
        return templating.render_template('results_plot.html', serverInfo=None,
                                          getOption=rhapi.db.option, __=rhapi.__)
    rhapi.ui.blueprint_add(bp)
    rhapi.ui.register_markdown("Lap Time Stats", "Results Plot", "Plots available [here](/results_plot)")

