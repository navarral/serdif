# -*- coding: utf-8 -*-
import requests
import urllib.parse
from jinja2 import Environment, FileSystemLoader
from collections import defaultdict
import json
import io

eeaAirQualityVars_Dict = {
    'http://dd.eionet.europa.eu/vocabulary/aq/pollutant/7': {
        'eeaVar': 'O3',
        'fullName': 'Ozone (air) - µg/m3',
        'unit': 'http://dd.eionet.europa.eu/vocabulary/uom/concentration/ug.m-3',
        'eeaInfo': 'http://dd.eionet.europa.eu/vocabulary/aq/pollutant/7',
    },
    'http://dd.eionet.europa.eu/vocabulary/aq/pollutant/7012': {
        'eeaVar': 'Pb',
        'fullName': 'Lead (precip+dry_dep) - µg/m2/day',
        'unit': 'http://dd.eionet.europa.eu/vocabulary/uom/concentration/ug.m-2.day-1',
        'eeaInfo': 'http://dd.eionet.europa.eu/vocabulary/aq/pollutant/7012',
    },
    'http://dd.eionet.europa.eu/vocabulary/aq/pollutant/7014': {
        'eeaVar': 'Cd',
        'fullName': 'Cadmium (precip+dry_dep) - µg/m2/day',
        'unit': 'http://dd.eionet.europa.eu/vocabulary/uom/concentration/ug.m-2.day-1',
        'eeaInfo': 'http://dd.eionet.europa.eu/vocabulary/aq/pollutant/7014',
    },
    'http://dd.eionet.europa.eu/vocabulary/aq/pollutant/7015': {
        'eeaVar': 'Ni',
        'fullName': 'Nickel (precip+dry_dep) - µg/m2/day',
        'unit': 'http://dd.eionet.europa.eu/vocabulary/uom/concentration/ug.m-2.day-1',
        'eeaInfo': 'http://dd.eionet.europa.eu/vocabulary/aq/pollutant/7015',
    },
    'http://dd.eionet.europa.eu/vocabulary/aq/pollutant/7018': {
        'eeaVar': 'As',
        'fullName': 'Arsenic (precip+dry_dep) - µg/m2/day',
        'unit': 'http://dd.eionet.europa.eu/vocabulary/uom/concentration/ug.m-2.day-1',
        'eeaInfo': 'http://dd.eionet.europa.eu/vocabulary/aq/pollutant/7018',
    },
    'http://dd.eionet.europa.eu/vocabulary/aq/pollutant/5': {
        'eeaVar': 'PM10',
        'fullName': 'Particulate matter < 10 um (aerosol) - ug/m3',
        'unit': 'http://dd.eionet.europa.eu/vocabulary/uom/concentration/ug.m-3',
        'eeaInfo': 'http://dd.eionet.europa.eu/vocabulary/aq/pollutant/5',
    },
    'http://dd.eionet.europa.eu/vocabulary/aq/pollutant/6001': {
        'eeaVar': 'PM2.5',
        'fullName': 'Particulate matter < 2.5 um (aerosol) - ug/m3',
        'unit': 'http://dd.eionet.europa.eu/vocabulary/uom/concentration/ug.m-3',
        'eeaInfo': 'http://dd.eionet.europa.eu/vocabulary/aq/pollutant/6001',
    },
    'http://dd.eionet.europa.eu/vocabulary/aq/pollutant/2': {
        'eeaVar': 'NO2',
        'fullName': 'Nitrogen dioxide (air) - ug/m3',
        'unit': 'http://dd.eionet.europa.eu/vocabulary/uom/concentration/ug.m-3',
        'eeaInfo': 'http://dd.eionet.europa.eu/vocabulary/aq/pollutant/2',
    },
    'http://dd.eionet.europa.eu/vocabulary/aq/pollutant/8': {
        'eeaVar': 'NO2',
        'fullName': 'Nitrogen dioxide (air) - ug/m3',
        'unit': 'http://dd.eionet.europa.eu/vocabulary/uom/concentration/ug.m-3',
        'eeaInfo': 'http://dd.eionet.europa.eu/vocabulary/aq/pollutant/8',
    },
    'http://dd.eionet.europa.eu/vocabulary/aq/pollutant/9': {
        'eeaVar': 'NOXasNO2',
        'fullName': 'Nitrogen oxides (air) - ug/m3',
        'unit': 'http://dd.eionet.europa.eu/vocabulary/uom/concentration/ug.m-3',
        'eeaInfo': 'http://dd.eionet.europa.eu/vocabulary/aq/pollutant/9',
    },
    'http://dd.eionet.europa.eu/vocabulary/aq/pollutant/1': {
        'eeaVar': 'SO2',
        'fullName': 'Sulphur dioxide (air) - ug/m3',
        'unit': 'http://dd.eionet.europa.eu/vocabulary/uom/concentration/ug.m-3',
        'eeaInfo': 'http://dd.eionet.europa.eu/vocabulary/aq/pollutant/1',
    },

    'http://dd.eionet.europa.eu/vocabulary/aq/pollutant/10': {
        'eeaVar': 'CO',
        'fullName': 'Carbon monoxide (air) - mg/m3',
        'unit': 'http://dd.eionet.europa.eu/vocabulary/uom/concentration/mg.m-3',
        'eeaInfo': 'http://dd.eionet.europa.eu/vocabulary/aq/pollutant/10',
    },
    'http://dd.eionet.europa.eu/vocabulary/aq/pollutant/20': {
        'eeaVar': 'C6H6',
        'fullName': 'Benzene (air) - ug/m3',
        'unit': 'http://dd.eionet.europa.eu/vocabulary/uom/concentration/ug.m-3',
        'eeaInfo': 'http://dd.eionet.europa.eu/vocabulary/aq/pollutant/20',
    },
    'http://dd.eionet.europa.eu/vocabulary/aq/pollutant/21': {
        'eeaVar': 'C6H5CH3',
        'fullName': 'Toluene (air) - ug/m3',
        'unit': 'http://dd.eionet.europa.eu/vocabulary/uom/concentration/ug.m-3',
        'eeaInfo': 'http://dd.eionet.europa.eu/vocabulary/aq/pollutant/21',
    },
    'http://dd.eionet.europa.eu/vocabulary/aq/pollutant/431': {
        'eeaVar': 'C6H5CH3',
        'fullName': 'Ethyl benzene (air) - ug/m3',
        'unit': 'http://dd.eionet.europa.eu/vocabulary/uom/concentration/ug.m-3',
        'eeaInfo': 'http://dd.eionet.europa.eu/vocabulary/aq/pollutant/431',
    },
    'http://dd.eionet.europa.eu/vocabulary/aq/pollutant/464': {
        'eeaVar': 'mpC6H4CH32',
        'fullName': 'm,p-Xylene (air) - ug/m3',
        'unit': 'http://dd.eionet.europa.eu/vocabulary/uom/concentration/ug.m-3',
        'eeaInfo': 'http://dd.eionet.europa.eu/vocabulary/aq/pollutant/464',
    },
    'http://dd.eionet.europa.eu/vocabulary/aq/pollutant/482': {
        'eeaVar': 'oC6H4CH32',
        'fullName': 'o-Xylene (air) - ug/m3',
        'unit': 'http://dd.eionet.europa.eu/vocabulary/uom/concentration/ug.m-3',
        'eeaInfo': 'http://dd.eionet.europa.eu/vocabulary/aq/pollutant/482',
    },
    'http://dd.eionet.europa.eu/vocabulary/aq/pollutant/351': {
        'eeaVar': 'Acenaphthene',
        'fullName': 'Acenaphthene - ng/m3',
        'unit': 'http://dd.eionet.europa.eu/vocabulary/uom/concentration/ng.m-3',
        'eeaInfo': 'http://dd.eionet.europa.eu/vocabulary/aq/pollutant/351',
    },
    'http://dd.eionet.europa.eu/vocabulary/aq/pollutant/352': {
        'eeaVar': 'Acenaphtylene',
        'fullName': 'Acenaphtylene (air+aerosol) - ng/m3',
        'unit': 'http://dd.eionet.europa.eu/vocabulary/uom/concentration/ng.m-3',
        'eeaInfo': 'http://dd.eionet.europa.eu/vocabulary/aq/pollutant/352',
    },
    'http://dd.eionet.europa.eu/vocabulary/aq/pollutant/435': {
        'eeaVar': 'Fluorene',
        'fullName': 'fluorene (air+aerosol) - ng/m3',
        'unit': 'http://dd.eionet.europa.eu/vocabulary/uom/concentration/ng.m-3',
        'eeaInfo': 'http://dd.eionet.europa.eu/vocabulary/aq/pollutant/435',
    },
    'http://dd.eionet.europa.eu/vocabulary/aq/pollutant/4406': {
        'eeaVar': 'Chrysene',
        'fullName': 'Chrysene (air+aerosol) - ng/m3',
        'unit': 'http://dd.eionet.europa.eu/vocabulary/uom/concentration/ng.m-3',
        'eeaInfo': 'http://dd.eionet.europa.eu/vocabulary/aq/pollutant/4406',
    },
    'http://dd.eionet.europa.eu/vocabulary/aq/pollutant/465': {
        'eeaVar': 'Naphtalene',
        'fullName': 'Naphtalene (air+aerosol) - ng/m3',
        'unit': 'http://dd.eionet.europa.eu/vocabulary/uom/concentration/ng.m-3',
        'eeaInfo': 'http://dd.eionet.europa.eu/vocabulary/aq/pollutant/465',
    },
    'http://dd.eionet.europa.eu/vocabulary/aq/pollutant/5012': {
        'eeaVar': 'PbinPM10',
        'fullName': 'Lead in PM10 (aerosol) - ug/m3',
        'unit': 'http://dd.eionet.europa.eu/vocabulary/uom/concentration/ug.m-3',
        'eeaInfo': 'http://dd.eionet.europa.eu/vocabulary/aq/pollutant/5012',
    },
    'http://dd.eionet.europa.eu/vocabulary/aq/pollutant/5014': {
        'eeaVar': 'CdinPM10',
        'fullName': 'Cadmium in PM10 (aerosol) - ng/m3',
        'unit': 'http://dd.eionet.europa.eu/vocabulary/uom/concentration/ng.m-3',
        'eeaInfo': 'http://dd.eionet.europa.eu/vocabulary/aq/pollutant/5014',
    },
    'http://dd.eionet.europa.eu/vocabulary/aq/pollutant/5015': {
        'eeaVar': 'NiinPM10',
        'fullName': 'Nickel in PM10 (aerosol) - ng/m3',
        'unit': 'http://dd.eionet.europa.eu/vocabulary/uom/concentration/ng.m-3',
        'eeaInfo': 'http://dd.eionet.europa.eu/vocabulary/aq/pollutant/5015',
    },
    'http://dd.eionet.europa.eu/vocabulary/aq/pollutant/5018': {
        'eeaVar': 'AsinPM10',
        'fullName': 'Arsenic in PM10 (aerosol) - ng/m3',
        'unit': 'http://dd.eionet.europa.eu/vocabulary/uom/concentration/ng.m-3',
        'eeaInfo': 'http://dd.eionet.europa.eu/vocabulary/aq/pollutant/5018',
    },
    'http://dd.eionet.europa.eu/vocabulary/aq/pollutant/5029': {
        'eeaVar': 'BaPinPM10',
        'fullName': 'Benzo(a)pyrene in PM10 (aerosol) - ng/m3',
        'unit': 'http://dd.eionet.europa.eu/vocabulary/uom/concentration/ng.m-3',
        'eeaInfo': 'http://dd.eionet.europa.eu/vocabulary/aq/pollutant/5029',
    },
    'http://dd.eionet.europa.eu/vocabulary/aq/pollutant/5380': {
        'eeaVar': 'BenzoFluorantheneinPM10',
        'fullName': 'Benzo(b,j,k)fluoranthene in PM10 (aerosol) - ng/m3',
        'unit': 'http://dd.eionet.europa.eu/vocabulary/uom/concentration/ng.m-3',
        'eeaInfo': 'http://dd.eionet.europa.eu/vocabulary/aq/pollutant/5380',
    },
    'http://dd.eionet.europa.eu/vocabulary/aq/pollutant/5419': {
        'eeaVar': 'DibenzoanthraceneinPM10',
        'fullName': 'Dibenzo(ah)anthracene in PM10 (aerosol) - ng/m3',
        'unit': 'http://dd.eionet.europa.eu/vocabulary/uom/concentration/ng.m-3',
        'eeaInfo': 'http://dd.eionet.europa.eu/vocabulary/aq/pollutant/5419',
    },
    'http://dd.eionet.europa.eu/vocabulary/aq/pollutant/5610': {
        'eeaVar': 'BenzoaanthraceneinPM10',
        'fullName': 'Benzo(a)anthracene in PM10 (aerosol) - ng/m3',
        'unit': 'http://dd.eionet.europa.eu/vocabulary/uom/concentration/ng.m-3',
        'eeaInfo': 'http://dd.eionet.europa.eu/vocabulary/aq/pollutant/5610',
    },
    'http://dd.eionet.europa.eu/vocabulary/aq/pollutant/5617': {
        'eeaVar': 'BenzobfluorantheneinPM10',
        'fullName': 'Benzo(b)fluoranthene in PM10 (aerosol) - ng/m3',
        'unit': 'http://dd.eionet.europa.eu/vocabulary/uom/concentration/ng.m-3',
        'eeaInfo': 'http://dd.eionet.europa.eu/vocabulary/aq/pollutant/5617',
    },
    'http://dd.eionet.europa.eu/vocabulary/aq/pollutant/5626': {
        'eeaVar': 'BenzokfluorantheneinPM10',
        'fullName': 'Benzo(k)fluoranthene in PM10 (aerosol) - ng/m3',
        'unit': 'http://dd.eionet.europa.eu/vocabulary/uom/concentration/ng.m-3',
        'eeaInfo': 'http://dd.eionet.europa.eu/vocabulary/aq/pollutant/5626',
    },
    'http://dd.eionet.europa.eu/vocabulary/aq/pollutant/5655': {
        'eeaVar': 'Indeno123cdpyreneinPM10',
        'fullName': 'Indeno_123cd_pyrene in PM10 (aerosol) - ng/m3',
        'unit': 'http://dd.eionet.europa.eu/vocabulary/uom/concentration/ng.m-3',
        'eeaInfo': 'http://dd.eionet.europa.eu/vocabulary/aq/pollutant/5655',
    },
    'http://dd.eionet.europa.eu/vocabulary/aq/pollutant/5759': {
        'eeaVar': 'BenzojfluorantheneinPM10',
        'fullName': 'Benzo(j)fluoranthene in PM10 (aerosol) - ng/m3',
        'unit': 'http://dd.eionet.europa.eu/vocabulary/uom/concentration/ng.m-3',
        'eeaInfo': 'http://dd.eionet.europa.eu/vocabulary/aq/pollutant/5759',
    },
    'http://dd.eionet.europa.eu/vocabulary/aq/pollutant/606': {
        'eeaVar': 'AnthraceneinPM10',
        'fullName': 'Anthracene (air+aerosol) - ng/m3',
        'unit': 'http://dd.eionet.europa.eu/vocabulary/uom/concentration/ng.m-3',
        'eeaInfo': 'http://dd.eionet.europa.eu/vocabulary/aq/pollutant/606',
    },
    'http://dd.eionet.europa.eu/vocabulary/aq/pollutant/622': {
        'eeaVar': 'Benzoghiperylene',
        'fullName': 'Benzo(ghi)perylene (air+aerosol) - ng/m3',
        'unit': 'http://dd.eionet.europa.eu/vocabulary/uom/concentration/ng.m-3',
        'eeaInfo': 'http://dd.eionet.europa.eu/vocabulary/aq/pollutant/622',
    },
    'http://dd.eionet.europa.eu/vocabulary/aq/pollutant/643': {
        'eeaVar': 'Fluoranthene',
        'fullName': 'fluoranthene (air+aerosol) - ng/m3',
        'unit': 'http://dd.eionet.europa.eu/vocabulary/uom/concentration/ng.m-3',
        'eeaInfo': 'http://dd.eionet.europa.eu/vocabulary/aq/pollutant/643',
    },
    'http://dd.eionet.europa.eu/vocabulary/aq/pollutant/712': {
        'eeaVar': 'Phenanthrene',
        'fullName': 'Phenanthrene (air+aerosol) - ng/m3',
        'unit': 'http://dd.eionet.europa.eu/vocabulary/uom/concentration/ng.m-3',
        'eeaInfo': 'http://dd.eionet.europa.eu/vocabulary/aq/pollutant/712',
    },
    'http://dd.eionet.europa.eu/vocabulary/aq/pollutant/715': {
        'eeaVar': 'Pyrene',
        'fullName': 'Pyrene (air+aerosol) - ng/m3',
        'unit': 'http://dd.eionet.europa.eu/vocabulary/uom/concentration/ng.m-3',
        'eeaInfo': 'http://dd.eionet.europa.eu/vocabulary/aq/pollutant/715',
    },
    'http://dd.eionet.europa.eu/vocabulary/aq/pollutant/4813': {
        'eeaVar': 'Hg0Hgreactive',
        'fullName': 'Total gaseous mercury (air+aerosol) - ng/m3',
        'unit': 'http://dd.eionet.europa.eu/vocabulary/uom/concentration/ng.m-3',
        'eeaInfo': 'http://dd.eionet.europa.eu/vocabulary/aq/pollutant/4813',
    },
    'http://dd.eionet.europa.eu/vocabulary/aq/pollutant/611': {
        'eeaVar': 'Benzoaanthracene',
        'fullName': 'Benzo(a)anthracene (precip+dry_dep) - ug/m2/day',
        'unit': 'http://dd.eionet.europa.eu/vocabulary/uom/concentration/ug.m-2.day-1',
        'eeaInfo': 'http://dd.eionet.europa.eu/vocabulary/aq/pollutant/611',
    },
    'http://dd.eionet.europa.eu/vocabulary/aq/pollutant/618': {
        'eeaVar': 'Benzobfluoranthene',
        'fullName': 'Benzo(b)fluoranthene (precip+dry_dep) - ug/m2/day',
        'unit': 'http://dd.eionet.europa.eu/vocabulary/uom/concentration/ug.m-2.day-1',
        'eeaInfo': 'http://dd.eionet.europa.eu/vocabulary/aq/pollutant/618',
    },
    'http://dd.eionet.europa.eu/vocabulary/aq/pollutant/627': {
        'eeaVar': 'Benzokfluoranthene',
        'fullName': 'Benzo(k)fluoranthene (precip+dry_dep) - ug/m2/day',
        'unit': 'http://dd.eionet.europa.eu/vocabulary/uom/concentration/ug.m-2.day-1',
        'eeaInfo': 'http://dd.eionet.europa.eu/vocabulary/aq/pollutant/627',
    },
    'http://dd.eionet.europa.eu/vocabulary/aq/pollutant/656': {
        'eeaVar': 'Indeno123cdpyrene',
        'fullName': 'Indeno-(1,2,3-cd)pyrene (precip+dry_dep) - ug/m2/day',
        'unit': 'http://dd.eionet.europa.eu/vocabulary/uom/concentration/ug.m-2.day-1',
        'eeaInfo': 'http://dd.eionet.europa.eu/vocabulary/aq/pollutant/656',
    },
    'http://dd.eionet.europa.eu/vocabulary/aq/pollutant/7029': {
        'eeaVar': 'BaP',
        'fullName': 'Benzo(a)pyrene (precip+dry_dep) - ug/m2/day',
        'unit': 'http://dd.eionet.europa.eu/vocabulary/uom/concentration/ug.m-2.day-1',
        'eeaInfo': 'http://dd.eionet.europa.eu/vocabulary/aq/pollutant/7029',
    },
    'http://dd.eionet.europa.eu/vocabulary/aq/pollutant/7419': {
        'eeaVar': 'Dibenzoahanthracene',
        'fullName': 'Dibenzo(ah)anthracene (precip+dry_dep) - ug/m2/day',
        'unit': 'http://dd.eionet.europa.eu/vocabulary/uom/concentration/ug.m-2.day-1',
        'eeaInfo': 'http://dd.eionet.europa.eu/vocabulary/aq/pollutant/7419',
    },
    'http://dd.eionet.europa.eu/vocabulary/aq/pollutant/1045': {
        'eeaVar': 'NH4inPM2.5',
        'fullName': 'Ammonium in PM2.5 (aerosol) - ug/m3',
        'unit': 'http://dd.eionet.europa.eu/vocabulary/uom/concentration/ug.m-3',
        'eeaInfo': 'http://dd.eionet.europa.eu/vocabulary/aq/pollutant/1045',
    },
    'http://dd.eionet.europa.eu/vocabulary/aq/pollutant/1046': {
        'eeaVar': 'NO3inPM2.5',
        'fullName': 'NO3- in PM2.5 (aerosol) - µg/m2/day',
        'unit': 'http://dd.eionet.europa.eu/vocabulary/uom/concentration/ug.m-3',
        'eeaInfo': 'http://dd.eionet.europa.eu/vocabulary/aq/pollutant/1046',
    },
    'http://dd.eionet.europa.eu/vocabulary/aq/pollutant/1047': {
        'eeaVar': 'SO42inPM2.5',
        'fullName': 'Sulphate in PM2.5 (aerosol) - ug/m3',
        'unit': 'http://dd.eionet.europa.eu/vocabulary/uom/concentration/ug.m-3',
        'eeaInfo': 'http://dd.eionet.europa.eu/vocabulary/aq/pollutant/1047',
    },
    'http://dd.eionet.europa.eu/vocabulary/aq/pollutant/1629': {
        'eeaVar': 'Ca2inPM2.5',
        'fullName': 'Calcium in PM2.5 (aerosol) - ug/m3',
        'unit': 'http://dd.eionet.europa.eu/vocabulary/uom/concentration/ug.m-3',
        'eeaInfo': 'http://dd.eionet.europa.eu/vocabulary/aq/pollutant/1629',
    },
    'http://dd.eionet.europa.eu/vocabulary/aq/pollutant/1631': {
        'eeaVar': 'ClinPM2.5',
        'fullName': 'Chloride in PM2.5 (aerosol - ug/m3',
        'unit': 'http://dd.eionet.europa.eu/vocabulary/uom/concentration/ug.m-3',
        'eeaInfo': 'http://dd.eionet.europa.eu/vocabulary/aq/pollutant/1631',
    },
    'http://dd.eionet.europa.eu/vocabulary/aq/pollutant/1657': {
        'eeaVar': 'KinPM2.5',
        'fullName': 'Potassium in PM2.5 (aerosol) - ug/m3',
        'unit': 'http://dd.eionet.europa.eu/vocabulary/uom/concentration/ug.m-3',
        'eeaInfo': 'http://dd.eionet.europa.eu/vocabulary/aq/pollutant/1657',
    },
    'http://dd.eionet.europa.eu/vocabulary/aq/pollutant/1659': {
        'eeaVar': 'Mg2inPM2.5',
        'fullName': 'Magnesium in PM2.5 (aerosol) - ug/m3',
        'unit': 'http://dd.eionet.europa.eu/vocabulary/uom/concentration/ug.m-3',
        'eeaInfo': 'http://dd.eionet.europa.eu/vocabulary/aq/pollutant/1659',
    },
    'http://dd.eionet.europa.eu/vocabulary/aq/pollutant/1668': {
        'eeaVar': 'NainPM2.5>',
        'fullName': 'Sodium in PM2.5 (aerosol) - ug/m3',
        'unit': 'http://dd.eionet.europa.eu/vocabulary/uom/concentration/ug.m-3',
        'eeaInfo': 'http://dd.eionet.europa.eu/vocabulary/aq/pollutant/1668',
    },
    'http://dd.eionet.europa.eu/vocabulary/aq/pollutant/1771': {
        'eeaVar': 'ECinPM2.5',
        'fullName': 'Elemental carbon in PM2.5 (aerosol) - ug/m3',
        'unit': 'http://dd.eionet.europa.eu/vocabulary/uom/concentration/ug.m-3',
        'eeaInfo': 'http://dd.eionet.europa.eu/vocabulary/aq/pollutant/1771',
    },
    'http://dd.eionet.europa.eu/vocabulary/aq/pollutant/1772': {
        'eeaVar': 'OCinPM2.',
        'fullName': 'Organic carbon in PM2.5 (aerosol) - ug/m3',
        'unit': 'http://dd.eionet.europa.eu/vocabulary/uom/concentration/ug.m-3',
        'eeaInfo': 'http://dd.eionet.europa.eu/vocabulary/aq/pollutant/1772',
    },
    'http://dd.eionet.europa.eu/vocabulary/aq/pollutant/38': {
        'eeaVar': 'NO',
        'fullName': 'Nitrogen monoxide (air) - ug/m3',
        'unit': 'http://dd.eionet.europa.eu/vocabulary/uom/concentration/ug.m-3',
        'eeaInfo': 'http://dd.eionet.europa.eu/vocabulary/aq/pollutant/38',
    },
    'http://dd.eionet.europa.eu/vocabulary/aq/pollutant/11': {
        'eeaVar': 'H2S',
        'fullName': 'Hydrogen sulphide (air) - ug/m3',
        'unit': 'http://dd.eionet.europa.eu/vocabulary/uom/concentration/ug.m-3',
        'eeaInfo': 'http://dd.eionet.europa.eu/vocabulary/aq/pollutant/11',
    },
}

metWeatherVars_Dict = {
    'rain': {
        'fullName': 'Precipitation Amount - mm',
        'unit': 'unit:MilliM',
        'metInfo': 'https://www.met.ie/climate/what-we-measure/rainfall',
        'envoVocLink': 'http://vocab.nerc.ac.uk/collection/A05/current/EV_RAIN/',
    },
    'temp': {
        'fullName': 'Air Temperature - ºC',
        'unit': 'unit:DEG_C ',
        'metInfo': 'https://www.met.ie/climate/what-we-measure/temperature',
        'envoVocLink': 'http://vocab.nerc.ac.uk/collection/A05/current/EV_AIRTEMP/'
    },
    'wetb': {
        'fullName': 'Wet Bulb Air Temperature - ºC',
        'unit': 'unit:DEG_C',
        'metInfo': 'https://www.met.ie/climate/what-we-measure/temperature',
        'envoVocLink': 'http://vocab.nerc.ac.uk/collection/P01/current/CWETZZ01/'
    },
    'dewpt': {
        'fullName': 'Dew Point Air Temperature - ºC',
        'unit': 'unit:DEG_C',
        'metInfo': 'https://www.met.ie/climate/what-we-measure/temperature',
        'envoVocLink': 'http://vocab.nerc.ac.uk/collection/P01/current/CDEWZZ01/'
    },
    'vappr': {
        'fullName': 'Vapour Pressure - hPa',
        'unit': 'unit:HectoPA',
        'metInfo': 'https://www.met.ie/climate/what-we-measure/water-vapour',
        'envoVocLink': 'http://vocab.nerc.ac.uk/collection/P07/current/CFSN0032/'
    },
    'rhum': {
        'fullName': 'Relative Humidity - %',
        'unit': 'unit:PERCENT',
        'metInfo': 'https://www.met.ie/climate/what-we-measure',
        'envoVocLink': 'http://vocab.nerc.ac.uk/collection/P01/current/CRELZZ01/',
    },
    'msl': {
        'fullName': 'Mean Sea Level Pressure - hPa',
        'unit': 'unit:HectoPA',
        'metInfo': 'https://www.met.ie/climate/what-we-measure',
        'envoVocLink': 'http://vocab.nerc.ac.uk/collection/P01/current/CDEWZZ01/'
    },
    'wdsp': {
        'fullName': 'Mean Hourly Wind Speed - kt',
        'unit': 'unit:KN',
        'metInfo': 'https://www.met.ie/climate/what-we-measure/wind',
        'envoVocLink': 'http://vocab.nerc.ac.uk/collection/A05/current/EV_WSPD/',
    },
    'wddir': {
        'fullName': 'Predominant Hourly wind Direction - º',
        'unit': 'unit:DEG',
        'metInfo': 'https://www.met.ie/climate/what-we-measure/wind',
        'envoVocLink': 'http://vocab.nerc.ac.uk/collection/A05/current/EV_WDIR/',
    },
    'sun': {
        'fullName': 'Sunshine duration - hours',
        'unit': 'unit:HR',
        'metInfo': 'https://www.met.ie/climate/what-we-measure/sunshine',
        'envoVocLink': 'http://vocab.nerc.ac.uk/collection/P07/current/CFSN0643/',
    },
    'vis': {
        'fullName': 'Visibility - m',
        'unit': 'unit:M',
        'metInfo': 'https://www.met.ie/climate/what-we-measure',
        'envoVocLink': 'http://vocab.nerc.ac.uk/collection/P07/current/CFSN0061/'
    },
    'clht': {
        'fullName': 'Cloud Ceiling Height - 100s feet',
        'unit': '<http://vocab.nerc.ac.uk/collection/P06/current/UUUU/>',
        'metInfo': 'https://www.met.ie/climate/what-we-measure',
        'envoVocLink': 'http://vocab.nerc.ac.uk/collection/P07/current/CFSN0747/'
    },
    'clamt': {
        'fullName': 'Cloud Amount - okta',
        'unit': '<http://vocab.nerc.ac.uk/collection/P06/current/UUUU/>',
        'metInfo': 'https://www.met.ie/climate/what-we-measure',
        'envoVocLink': 'http://vocab.nerc.ac.uk/collection/P07/current/CFSN0745/'
    }

}


def genMetadataFile(queryTimeUrl, timeUnit, spAgg, wLag, wLen, evEnvoDict,
                    fileSize, qText, eeVars, username, password):
    # Load environment for jinja2 templates
    file_loader = FileSystemLoader('templates')
    env = Environment(loader=file_loader)
    # 1. Generate mapping file from template
    # Load eea template file
    metaMap = env.get_template('Envo-Event_data_example_template.ttl')
    # Set data dictionary for input
    datasetVersion = '20211012T120000'
    # Edit evEnvoDict input
    dd = defaultdict(list)

    for k in evEnvoDict.keys():
        tt = evEnvoDict[k]
        for key, val in tt.items():
            dd[key].append(val)

    evEnvoDict_e = dict(dd)

    def flatten(d):
        return [i for b in [[i] if not isinstance(i, list) else flatten(i) for i in d] for i in b]

    # Dictionaries to translate timeUnit to query SPARQL query parameters
    selTimeUnit = {'hour': 'HOURS',
                   'day': 'DAYS',
                   'month': 'MONTHS',
                   'year': 'YEARS',
                   }
    selTimeRes = {'hour': 'PT1H',
                  'day': 'P1D',
                  'month': 'P1M',
                  'year': '?P1Y',
                  }
    # Extract environmental variables information from dictionaries above
    eeVarUp = []
    eeVarLow = []
    eeVarNameUnitUp = []
    eeVarNameUnit = []
    eeVarUnit = []
    eeVarInfo = []
    eeVarEnvoLink = []
    for eVar in eeVars:
        if eVar.lower() in metWeatherVars_Dict:
            # Capitalize only first letter for properties
            eeVarUp.append(eVar.upper())
            # Lower case variables for label
            eeVarLow.append(eVar.lower())
            # Full name and unit for the variables Upper case for comment at the start
            eeVarNameUnitUp.append(metWeatherVars_Dict[eVar.lower()]['fullName'].upper())
            # Full name and unit for the variables
            eeVarNameUnit.append(metWeatherVars_Dict[eVar.lower()]['fullName'])
            # Variable unit
            eeVarUnit.append(metWeatherVars_Dict[eVar.lower()]['unit'])
            # Met Eireann or EEA information about the variable
            eeVarInfo.append(metWeatherVars_Dict[eVar.lower()]['metInfo'])
            # The NERC Vocabulary Server (NVS) information about the variable
            eeVarEnvoLink.append(metWeatherVars_Dict[eVar.lower()]['envoVocLink'])
        else:
            for k in eeaAirQualityVars_Dict.keys():
                if eVar == eeaAirQualityVars_Dict[k]['eeaVar']:
                    # Capitalize only first letter for properties
                    eeVarUp.append(eVar)
                    # Lower case variables for label
                    eeVarLow.append(eVar.lower())
                    # Full name and unit for the variables Upper case for comment at the start
                    eeVarNameUnitUp.append(eeaAirQualityVars_Dict[k]['fullName'].upper())
                    # Full name and unit for the variables
                    eeVarNameUnit.append(eeaAirQualityVars_Dict[k]['fullName'])
                    # Variable unit
                    eeVarUnit.append('<' + eeaAirQualityVars_Dict[k]['unit'] + '>')
                    # Met Eireann or EEA information about the variable
                    eeVarInfo.append(str(eeaAirQualityVars_Dict[k]['eeaInfo']))
                    # The NERC Vocabulary Server (NVS) information about the variable
                    eeVarEnvoLink.append('')

    # Query geometry metadata information
    # 1.3.Fire query and convert results to json (dictionary)
    qGeoMetadata = requests.post(
        'https://serdif-example.adaptcentre.ie/repositories/repo-serdif-events-ie',
        data={'query': '''
                PREFIX geo: <http://www.opengis.net/ont/geosparql#>
                PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
                SELECT *
                WHERE { 
                    VALUES ?LOI {''' + ''.join([' "' + envoLocVal + '"@en ' for envoLocVal in set(evEnvoDict_e['LOI_ev'])]) + '''}
                    ?county
                        a geo:Feature, <http://ontologies.geohive.ie/osi#County> ;
                        rdfs:label ?LOI ;
                        geo:hasGeometry/geo:asWKT ?countyGeo .
                } 
                '''
              },
        auth=(username, password),
        headers={'Accept': 'application/sparql-results+json'}
    ).text
    # 1.4.Return results
    jGeoMetadata = json.loads(qGeoMetadata)['results']['bindings']
    rGeoMetadata_geo = ['<' + geoIRI['county']['value'] + '>' for geoIRI in jGeoMetadata]
    rGeoMetadata_geoLit = ['"""' + geoLit['countyGeo']['value'] + '"""^^geo:wktLiteral' for geoLit in jGeoMetadata]

    # External data sets used to construct the query
    extDataUsed = ['<' + envDS + '>' for envDS in set(flatten(evEnvoDict_e['envoDS']))]

    metaMap_dict = {
        'version': datasetVersion,
        'queryTime': queryTimeUrl,
        'queryDateTime': queryTimeUrl.replace('%3A', ':'),
        'countyName': ' '.join(set(evEnvoDict_e['LOI_ev'])),
        'timeUnit': selTimeUnit[timeUnit],
        'aggMethod': spAgg,
        'wLag': wLag,
        'wLen': wLen,
        'extDataSetsUsed': ', '.join(extDataUsed) ,
        'countyGeom': ', '.join(rGeoMetadata_geo),
        'countyGeomGeo': ', '.join(rGeoMetadata_geo),
        'timeRes': selTimeRes[timeUnit],
        'fileSize': fileSize,
        'startDateTime': min(evEnvoDict_e['dateStart']),
        'endDateTime': max(evEnvoDict_e['dateLag']),
        'countyGeomLiteral': ', '.join(rGeoMetadata_geoLit),
        'queryText': qText,
        'eeVars': eeVarUp,
        'eeVarsD': zip(*[eeVarNameUnitUp, eeVarUp, eeVarLow,
                         eeVarNameUnit, eeVarUnit, eeVarInfo, eeVarEnvoLink]),
    }
    outMap = metaMap.stream(data=metaMap_dict)
    # Export resulting mapping
    #outMap.dump('metadataExports/metadata-ee-' + datasetVersion + '-' + queryTimeUrl + '.ttl')
    fileobj = io.StringIO()
    outMap.dump(fileobj)
    outMapRend = fileobj.getvalue()
    return outMapRend



if __name__ == '__main__':
    genMetadataFile()



