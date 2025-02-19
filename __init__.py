'''Results Plots'''
import logging
import os
from eventmanager import Evt
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
import itertools
from flask import templating
from flask.blueprints import Blueprint


class Results_plot():
    def __init__(self, rhapi):
        self.logger = logging.getLogger(__name__)
        self._rhapi = rhapi

    def init_plugin(self, args):
        self.logger.info("Results Plot Plugin intialised")


    def update_plot(self, args):

        raceclass = self._rhapi.db.raceclasses
        raceclass_results = self._rhapi.db.raceclass_results(raceclass[0])

        if raceclass_results['by_consecutives']:
            self.logger.info("rplots - creating plot")
            self.logger.info([i['callsign'] for i in raceclass_results['by_consecutives']])
            pilot_race_order = [i['pilot_id'] for i in raceclass_results['by_consecutives']]
            self.logger.info([i['pilot_id'] for i in raceclass_results['by_consecutives']])
            self.logger.info([i['consecutives'] for i in raceclass_results['by_consecutives']])
            self.logger.info([i['consecutives_base'] for i in raceclass_results['by_consecutives']])
            pilots = self._rhapi.db.pilots

            pilot_ids = []
            pilot_names = []
            for i in range(len(pilots)):
                pilot_ids.append(pilots[i].id)
                pilot_names.append(pilots[i].callsign)

            races = self._rhapi.db.pilotruns
            max_race_id = max(race.race_id for race in races)


            pilot_list = []
            for i in range(len(pilots)):
                pilot_list.append([])

            for r in range(len(races)):
                if races[r].pilot_id != 0:
                    pilot_list[pilot_ids.index(races[r].pilot_id)].append(races[r].id)

            pilot_lap_times = []
            for i in range(len(pilots)):
                pilot_lap_times.append([])

            for i in range(len(pilot_list)):
                for j in range(len(pilot_list[i])):
                    laps = self._rhapi.db.laps_by_pilotrun(pilot_list[i][j])
                    temp_laps = [lap.lap_time_formatted for lap in laps if lap.deleted == 0]
                    for k in range(len(temp_laps)):
                        if k != 0:
                            times_in_seconds = (float(temp_laps[k].split(":")[0] * 60) +
                                                float(temp_laps[k].split(":")[1]))
                            pilot_lap_times[i].append(times_in_seconds)

            re_order_pilot_lap_times = []
            re_order_pilot_names = []
            for i in pilot_race_order:
                re_order_pilot_lap_times.append(pilot_lap_times[pilot_ids.index(i)])
                re_order_pilot_names.append(
                    [pilot_names[pilot_ids.index(i)] for j in range(len(pilot_lap_times[pilot_ids.index(i)]))])

            data_list = {"Pilot": list(itertools.chain(*re_order_pilot_names)),
                         "Lap Time": list(itertools.chain(*re_order_pilot_lap_times))}
            df = pd.DataFrame.from_dict(data_list)

            fig, ax = plt.subplots(figsize=(10, 7))

            palette = sns.color_palette("tab20", len(pilot_race_order))
            medianprops = {
                "color": "fuchsia",
                "linewidth": 3,
                "linestyle": "-"
            }
            sns.boxplot(data=df, x="Lap Time", y="Pilot", hue="Pilot", palette=palette, orient="h", ax=ax,
                        legend=False,
                        medianprops=medianprops)
            sns.stripplot(data=df, x="Lap Time", y="Pilot", hue="Pilot", palette='dark:Black',
                          ax=ax, size=4, jitter=True,
                          alpha=0.6,
                          dodge=False)
            ax.set_xlabel('Lap Time (seconds)', color="black")
            for label, color in zip(ax.get_yticklabels(), palette):
                label.set_color(color)
            min_x, max_x = df["Lap Time"].min(), df["Lap Time"].max()
            ax.set_xticks(range(int(min_x // 5) * 5, int(max_x // 5) * 5 + 5, 5))  # Ticks every 5 seconds
            ax.xaxis.grid(True, linestyle='--', alpha=0.4, color="gray")
            plt.savefig("plugins/rh_rplots/static/boxplot.png", dpi=300, bbox_inches='tight')
            plt.show()
            self.logger.info("Plot Done")
        else:
            self.logger.info("No results to plot")


def initialize(rhapi):
    results_plot = Results_plot(rhapi)
    rhapi.events.on(Evt.STARTUP, results_plot.init_plugin)
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
                                          getOption=rhapi.db.option,__=rhapi.__)
    rhapi.ui.blueprint_add(bp)
    rhapi.ui.register_markdown("Lap Time Stats", "Results Plot", "Plots available [here](/results_plot)")


