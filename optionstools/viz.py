import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
import os
import tempfile
import time
from scipy.interpolate import make_interp_spline, BSpline
from PIL import Image


class ProfitPlots(object):
    
    def __init__(self, optimizers):
        """
        Attributes:
        -----------
        optimizers : list[optionstools.StrategyOptimizer]
            list of the strategy optimizers to plot
        current_price : float
            current equity price
        future_price : float
            predicted future price
        """
        self.optimizers = optimizers
        self.current_price = optimizers[0].current_price
        self.future_price = optimizers[0].future_price
        
    
    def _plot(self):
        
        def add_plot(ax, name, profit_array, max_profit):
            ax.set_title(name, weight=1000, loc='left', pad=15, fontsize=18, color='#3d3d3d')
            ax.set_xlabel('Underlying Stock Price (S)', weight=800, labelpad=15, color='#3d3d3d')
            ax.set_ylabel('Profit', weight=800, color='#3d3d3d')
            ax.xaxis.grid(alpha=.5)
            ax.spines['right'].set_visible(False)
            ax.spines['top'].set_visible(False)
            ax.spines['bottom'].set_visible(False)
            ax.spines['left'].set_visible(False)
            ax.hlines([0], min(profit_array[:,0]), max(profit_array[:,0]), color='grey', linewidth=3)

            formatter = ticker.FormatStrFormatter('$%1.2f')
            ax.yaxis.set_major_formatter(formatter)
            ax.xaxis.set_major_formatter(formatter)

            for tick in ax.yaxis.get_major_ticks():
                tick.label1.set_visible(True)
                tick.label2.set_visible(False)

            # fit curve
            xnew = np.linspace(min(profit_array[:,0]),max(profit_array[:,0]), 300) 
            spl = make_interp_spline(profit_array[:,0], profit_array[:,1], k=3)
            power_smooth = spl(xnew)

            # conditional formatting
            pos_curve = power_smooth.copy()
            neg_curve = power_smooth.copy()

            pos_curve[pos_curve <= 0] = np.nan
            neg_curve[neg_curve > 0] = np.nan

            ax.fill_between(xnew, pos_curve, 0, alpha=0.05, color='lime')
            ax.fill_between(xnew, neg_curve, 0, alpha=0.05, color='red')

            ax.plot(xnew, pos_curve, linewidth=.7, color='lime')
            ax.plot(xnew, neg_curve, linewidth=.7, color='red')

            # annotations
            ax.hlines([max_profit], min(profit_array[:,0]), self.future_price, color='grey', linewidth=1, linestyle='--')

            annotation_alignment = ('left', 'right') if self.current_price > self.future_price else ('right', 'left')
            max_profit = max(power_smooth) * 1.1

            ax.vlines([self.future_price], 0, max_profit, color='grey', linewidth=1, linestyle='--')
            ax.vlines([self.current_price], 0, max_profit, color='grey', linewidth=1, linestyle='--')

            ax.annotate('Current Price', xy=(self.current_price, max_profit),  xycoords='data',
                        xytext=(self.current_price, max_profit), textcoords='data',
                        horizontalalignment=annotation_alignment[0], verticalalignment='bottom',
                        )
            ax.annotate('Predicted Price', xy=(self.future_price, max_profit),  xycoords='data',
                        xytext=(self.future_price, max_profit), textcoords='data',
                        horizontalalignment=annotation_alignment[1], verticalalignment='bottom',
                        )

        plot_count = len(self.optimizers)
        if plot_count > 1:
            fig, axes = plt.subplots(plot_count//2 + 1, 2, figsize=(18, 5 * (plot_count//2 + 1)))
            if not plot_count % 2 == 0:
                axes[-1, -1].axis('off')
        else:
            fig, axes = plt.subplots(figsize=(10,6))

        axes = np.ravel(axes)
        fig.patch.set_facecolor('white')
        for i, opt in enumerate(self.optimizers):
            diff = abs(self.future_price - self.current_price)
            s_samples = np.linspace(self.current_price - 2 * diff, self.current_price + 2 * diff, 100)
            profits = [opt.get_profit(s) for s in s_samples]
            profit_array = np.c_[s_samples, profits]
            add_plot(axes[i], opt.strategy.__class__.__name__, profit_array, opt.max_profit)
        
        plt.subplots_adjust(hspace=0.5)
    
    def show(self):
        self._plot()
        plt.show()

    def save_and_open(self, filename=None):
        tmp = tempfile.gettempdir()
        filename = filename if filename else os.path.join(tmp, f'optionstools_profit_plots_{round(time.time())}.png')
        self._plot()
        plt.savefig(filename)
        img = Image.open(filename)
        img.show()
