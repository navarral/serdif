import warnings
from rpy2.rinterface import RRuntimeWarning
warnings.filterwarnings('ignore', category=RRuntimeWarning)
from rpy2.robjects.packages import importr
from rpy2.robjects import pandas2ri


# Pnadas dataframe to polar plot from openair R package
def dfToPolar(df, dVal_Polarplot, fileName):
    pandas2ri.activate()
    r_df = pandas2ri.py2rpy(df)
    openair = importr('openair')
    grdevices = importr('grDevices')
    grdevices.png(file=fileName, width=800, height=700)
    openair.polarPlot(mydata=r_df, x='Wdsp', wd='Wddir', pollutant=dVal_Polarplot,
                          k=10, fontsize=34)
    grdevices.dev_off()
    return 'Polar plot ready'


if __name__ == '__main__':
    dfToPolar()