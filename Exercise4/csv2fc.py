# -*- coding: utf-8 -*-
import arcpy
import os

def CreateGDB(dir, gdbName):
    gdb = os.path.join(dir, gdbName + ".gdb")
    if not os.path.exists(gdb):
        arcpy.CreateFileGDB_management(dir, gdbName + ".gdb")
    print ("GDB Created, Path: {0}".format(gdb))
    return gdb


if __name__ == "__main__":
    arcpy.env.workspace = CreateGDB(".","data")
    sr = arcpy.SpatialReference(4326)
    csvpath = "./pois.txt"
    arcpy.MakeXYEventLayer_management(
    csvpath, "lng", "lat", "temp", arcpy.SpatialReference(4326))
    arcpy.CopyFeatures_management("temp", "imported_poi")
    arcpy.Delete_management("temp")
    print(arcpy.ListFeatureClasses())