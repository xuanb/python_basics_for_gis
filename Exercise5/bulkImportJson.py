
# - *- coding: utf- 8 - *-
import arcpy
import os
import geopandas as gpd

# create gdb
if not os.path.exists("./boarders.gdb"):
    arcpy.CreateFileGDB_management("./", "boarders.gdb")

# create a scrach workspace
scratch = "./scratch"
if os.path.exists(scratch):
    os.rmdir(scratch)
os.makedirs(scratch)
# setup workspace
arcpy.env.workspace = "./boarders.gdb"
arcpy.env.overwriteOutput = True

# process the json files
for filename in os.listdir("./json/"):
    if arcpy.Exists(filename[:-5]):
        arcpy.Delete_management(filename[:-5])
    if filename.endswith(".json"):
        file = "./json/{0}".format(filename)
        df = gpd.read_file(file, encoding = 'utf-8')
        print(df.head())
        df.to_file(u"{0}/temp.shp".format(scratch), encoding='utf-8')
        arcpy.CopyFeatures_management("{0}/temp.shp".format(scratch),filename[:-5])
        arcpy.Delete_management("{0}/temp.shp".format(scratch))
        print("{0} Processed".format(filename))

if os.path.exists(scratch):
    os.rmdir(scratch)