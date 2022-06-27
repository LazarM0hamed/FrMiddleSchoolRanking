#!/bin/env python

import pandas as pd
import matplotlib.pyplot as plt
import requests
import argparse
import os
import math 

def get_dist(lon1, lat1, lon2, lat2):
    # approximate radius of earth in km
    R = 6373.0
    lat1 = math.radians(lat1)
    lon1 = math.radians(lon1)
    lat2 = math.radians(lat2)
    lon2 = math.radians(lon2)
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distance_km = R * c
    return round(distance_km, 2)

def log(message): print('>>> '+message)

def getColor(index):
    colors = ['blue', 'red', 'orange', 'dimgray', 'lightcoral', 'navy', 'maroon',
              'gold', 'olive', 'tomato', 'cyan', 'lightgreen','sienna', 'peachpuff',
              'pink',  'violet', 'deepskyblue', 'turquoise', 'black']
    index %= len(colors)
    return colors[index]

class FrMiddleSchool:
    def __init__(self, myRegion, myTown, myDepartments, myLongLat, session=2020, mySuccessRate=97, myTresBienRate=0.1):
        self.myRegion      = myRegion
        self.myTown        = myTown
        self.myDepartments = myDepartments
        self.myLongLat     = myLongLat
        self.session       = session 
        self.mySuccessRate = mySuccessRate
        self.myTresBienRate= myTresBienRate

        ## Download data
        if not os.path.exists('fr-en-dnb-par-etablissement.csv'):
            response = requests.get('https://data.education.gouv.fr/explore/dataset/fr-en-dnb-par-etablissement/download/?format=csv&timezone=Europe/Berlin&lang=fr&use_labels_for_header=true&csv_separator=%3B')
            open('fr-en-dnb-par-etablissement.csv', "wb").write(response.content)

        if not os.path.exists('fr-en-adresse-et-geolocalisation-etablissements-premier-et-second-degre.csv'):
            response = requests.get('https://data.education.gouv.fr/explore/dataset/fr-en-adresse-et-geolocalisation-etablissements-premier-et-second-degre/download/?format=csv&timezone=Europe/Berlin&lang=fr&use_labels_for_header=true&csv_separator=%3B')
            open('fr-en-adresse-et-geolocalisation-etablissements-premier-et-second-degre.csv', "wb").write(response.content)

        ## Create dataframe
        self.df = pd.read_csv('fr-en-dnb-par-etablissement.csv', sep=';')

        self.list_departments = self.df['Libellé département'].unique()
        self.list_regions     = self.df['Libellé région'].unique()
        self.list_towns       = self.df['Libellé commune'].unique()

    def prepare(self):
        log('Total records: {}'.format(self.df.shape[0]))

        log('Keep only COLLEGE related to my region {} and session {}:'.format(self.myRegion, self.session))
        self.df = self.df.loc[(self.df['Libellé région'] == self.myRegion) & (self.df["Type d'etablissement"]=='COLLEGE') & (self.df['Session'] == self.session)]
        log('Remaining records: {}'.format(self.df.shape[0]))

        ## Get Addresses
        df_addr = pd.read_csv('fr-en-adresse-et-geolocalisation-etablissements-premier-et-second-degre.csv', sep=';')
        self.df = self.df.merge(df_addr, how='left', left_on="Numero d'etablissement", right_on='Code établissement')

        log('Keep only records related to my departments {}:'.format(self.myDepartments))
        self.df = self.df[self.df['Libellé département'].isin(self.myDepartments)]
        log('Remaining records: {}'.format(self.df.shape[0]))

        log('Filter by success rate threshold {}%:'.format(self.mySuccessRate))
        self.df['Taux de réussite'] = self.df['Taux de réussite'].apply(lambda x: float(x[:-1].replace(',','.')))
        self.df = self.df[self.df['Taux de réussite'] >= self.mySuccessRate]
        log('Remaining records: {}'.format(self.df.shape[0]))

        sorterIndex = dict(zip(self.myDepartments, range(len(self.myDepartments))))
        self.df['Rank Departement'] = self.df['Libellé département'].map(sorterIndex)
        self.df['Taux très bien %'] = round(self.df['Admis Mention très bien'] / self.df['Inscrits'], 2)
        log('Filter by tres bien rate threshold {}%:'.format(self.mySuccessRate))
        self.df = self.df[self.df['Taux très bien %'] >= self.myTresBienRate]
        log('Remaining records: {}'.format(self.df.shape[0]))

        log('Compute distances:')
        self.df['Distance'] = self.df.apply(lambda x: get_dist(x['Longitude'], x['Latitude'], self.myLongLat[0], self.myLongLat[1]), axis=1)
        self.df['Rank Distance'] = self.df['Distance'].max() - self.df['Distance']

    def sort(self):
        log("Sort records by : 'Taux très bien %', 'Admis', 'Taux de réussite', 'Rank Distance', 'Rank Departement'")
        self.df = self.df.sort_values(by=['Taux très bien %', 'Admis', 'Taux de réussite', 'Rank Distance', 'Rank Departement'], ascending=False).reset_index()

        log("Write output : 'college_selection.csv'")
        self.df.to_csv('college_selection.csv')

    def plot(self):
        fig, ax = plt.subplots(1, figsize=(12,6))
        sc_s = []
        tt_s = []

        def scatter(df_, df_filter, marker, c, sc_s, tt_s, label):
            df__ = df_[df_filter]
            sc_s.append(ax.scatter(x=df__['Longitude'], y=df__['Latitude'], marker=marker, c=c, label=label))
            tt_s.append(df__.index)

        def hover(event):
            for i, sc in enumerate(sc_s):
                cont, ind = sc.contains(event)
                if cont:
                    # change annotation position
                    annot.xy = (event.xdata, event.ydata)
                    index = tt_s[i][ind['ind'][0]]

                    row = self.df.iloc[index]
                    txt = '{} {} {} TB{:.2f} R{:.2f}'.format(index, row['Patronyme'], row['Libellé commune'], row['Taux très bien %'], row['Taux de réussite'])
                    # write the name of every point contained in the event
                    annot.set_text(txt)
                    annot.set_visible(True)
                    event.canvas.draw()
                    break
                else:
                    annot.set_visible(False)

        df_ = self.df[self.df["Secteur d'enseignement"]=='PRIVE']
        for i, dep in enumerate(self.myDepartments):
            scatter(df_, df_['Libellé département']==dep, '^', getColor(i), sc_s, tt_s, 'Private '+dep)
        scatter(df_, df_['Libellé commune']==self.myTown, '^', 'green', sc_s, tt_s, 'Private '+self.myTown)

        df_ = self.df[self.df["Secteur d'enseignement"]=='PUBLIC']
        for i, dep in enumerate(self.myDepartments):
            scatter(df_, df_['Libellé département']==dep, 'o', getColor(i), sc_s, tt_s, 'Public '+dep)
        scatter(df_, df_['Libellé commune']==self.myTown, 'o', 'green', sc_s, tt_s, 'Public '+self.myTown)

        ax.legend()
        ax.set_title('Middle School Ranking');

        for index, row in self.df.iterrows():
            ax.annotate('{}'.format(index), (row['Longitude'], row['Latitude']))

        annot = ax.annotate("", xy=(0,0), xytext=(5,5),textcoords="offset points")
        annot.set_visible(False)

        fig.canvas.mpl_connect("motion_notify_event", hover)
        #circle1 = plt.Circle(self.myLongLat, 0.2, color='cyan')
        #ax.add_patch(circle1)
        plt.show()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('region', help='Your region.')
    parser.add_argument('deps', help='Your departments list eg: "HAUTS-DE-SEINE,PARIS,VAL-DE-MARNE".')
    parser.add_argument('town', help='Your town.')
    parser.add_argument('longlat', help='Your coordinates (longitude, latitude), eg "2.487970,48.846350".')
    parser.add_argument('--session', default=2020, help='Session number.')
    parser.add_argument('--successRate', default=97, help='Success rate %%.')
    parser.add_argument('--tresBienRate', default=0.1, help='Tres bien rate between [0,1].')

    args = parser.parse_args()

    MY_REGION      = args.region.upper()
    MY_TOWN        = args.town.upper()
    MY_DEPARTMENTS = args.deps.upper().split(',')

    try:
        MY_LONG_LAT = args.longlat.split(',')
        longitude = float(MY_LONG_LAT[0])
        latitude  = float(MY_LONG_LAT[1])
        MY_LONG_LAT = (longitude, latitude)
    except:
        print('Error: invalid longlat formats')
        return -2
    
    fr = FrMiddleSchool(MY_REGION, MY_TOWN, MY_DEPARTMENTS, MY_LONG_LAT,
                        session = args.session,
                        mySuccessRate = args.successRate,
                        myTresBienRate = args.tresBienRate)

    if not MY_REGION in fr.list_regions:
        print("Valid regions list:")
        print(fr.list_regions)
        return -1

    if not MY_TOWN in fr.list_towns:
        print("Valid towns list:")
        for t in fr.list_towns:
            print(t)
        return -1   

    for dep in MY_DEPARTMENTS:
        if not dep in fr.list_departments:
            print("Valid departments list:")
            print(fr.list_departments)
            return -1

    fr.prepare()
    fr.sort()
    fr.plot()

if __name__ == '__main__':
    main()
