# -*- coding: utf-8 -*-
import arcpy
import os
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt


class HotSpotAnalysis:
    def __init__(self, dir, gdbName, gridName, districts=None):
        '''
        : __init: 初始化方法
        dir: excel 文件所在路径，文件为POI数据，坐标为经纬度（4326），lng & lat
        gdbName: 新建GDB名称，存储与dir文件夹中
        districts: 分析区域
        '''
        self.dir = dir
        self.gdbName = gdbName
        self.gridName = gridName
        self.districts = districts
        self.weights = {
            "edu_num": 2,
            "food_num": 3,
            "siteseeing_num": 5,
            "shopping_num": 3,
            "infrastructure_num": 1,
            "medicine_num": 1,
        }
        arcpy.env.workspace = self.CreateGDB(dir, gdbName)
        arcpy.env.overwriteOutput = True
        self.Excel2FC(dir)
        self.GenerateHexGrid(gridName)
        self.CountAllInGrids(gridName)
        self.DeleteEmptyGrids(gridName)
        self.Analysis(gridName)

    def CreateGDB(self, dir, gdbName):
        gdb = os.path.join(dir, gdbName + ".gdb")
        if not os.path.exists(gdb):
            arcpy.CreateFileGDB_management(dir, gdbName + ".gdb")
        print("GDB Created, Path: {0}".format(gdb))
        return gdb

    def Excel2FC(self, dir):
        for filename in os.listdir(dir):
            if filename.endswith(".xlsx"):
                file = os.path.join(dir, filename)
                df = pd.read_excel(file, usecols=lambda x: 'Unnamed' not in x)
                if os.path.isfile('csvfile.csv'):
                    os.remove('csvfile.csv')
                df.to_csv('csvfile.csv', encoding='utf-8', index=False)
                arcpy.MakeXYEventLayer_management(
                    'csvfile.csv', "lng", "lat", "temp", arcpy.SpatialReference(4326))
                arcpy.CopyFeatures_management("temp",  filename[:-5])
                arcpy.Delete_management("temp")
                print(u"Created Feature Class {0}".format(filename[:-5]))
        if os.path.isfile('csvfile.csv'):
            os.remove('csvfile.csv')

    def GetWorkSpaceExtent(self):
        minX = 1000000000
        maxX = 0
        minY = 1000000000
        maxY = 0
        for featureClass in arcpy.ListFeatureClasses():
            minX = minX if arcpy.Describe(
                featureClass).extent.XMin > minX else arcpy.Describe(featureClass).extent.XMin
            maxX = maxX if arcpy.Describe(
                featureClass).extent.XMax < maxX else arcpy.Describe(featureClass).extent.XMax
            minY = minY if arcpy.Describe(
                featureClass).extent.YMin > minY else arcpy.Describe(featureClass).extent.YMin
            maxY = maxY if arcpy.Describe(
                featureClass).extent.YMax < maxY else arcpy.Describe(featureClass).extent.YMax
        return arcpy.Extent(minX, minY, maxX, maxY)

    def GenerateHexGrid(self, gridName):
        hex_extent = self.GetWorkSpaceExtent()
        spatial_ref = arcpy.SpatialReference(4326)
        arcpy.GenerateTessellation_management(
            gridName, hex_extent, "HEXAGON", "0.5 SquareKilometers", spatial_ref)
        # self.plotFC(arcpy.env.workspace, gridName)

    def plotFC(self, gdb, fcName, alpha=0.5, column=None):
        df = gpd.read_file(arcpy.env.workspace, layer=fcName)
        df.plot(alpha=0.5, figsize=(11, 11), column=column)
        plt.draw()
        plt.pause(0.1)

    def CountAllInGrids(self, gridName):
        for l in arcpy.ListFeatureClasses():
            desc = arcpy.Describe(l)
            if desc.shapeType == "Point":
                self.CountPointsInGrids(gridName, l)

    def CountPointsInGrids(self, gridName, poi):
        arcpy.SpatialJoin_analysis(gridName, poi, "temp", "JOIN_ONE_TO_ONE")
        arcpy.AlterField_management("temp", "Join_Count", poi+"_num")
        for field in arcpy.ListFields("temp"):
            if "_num" not in field.name and not field.required:
                arcpy.DeleteField_management("temp", field.name)
        arcpy.CopyFeatures_management("temp", gridName)
        arcpy.Delete_management("temp")
        print("Layer {0} has been processed".format(poi))

    def DeleteEmptyGrids(self, gridName):
        arcpy.MakeFeatureLayer_management(gridName, "grid_layer")
        expression = ""
        for field in arcpy.ListFields(gridName):
            if "_num" in field.name:
                expression += field.name + " < 1 AND "
        expression = expression[:-5]
        print expression
        arcpy.SelectLayerByAttribute_management("grid_layer",
                                                "NEW_SELECTION",
                                                expression)
        print("Deleting {0} rows in {1}".format(
            arcpy.GetCount_management("grid_layer").getOutput(0), gridName))
        if int(arcpy.GetCount_management("grid_layer").getOutput(0)) > 0:
            arcpy.DeleteRows_management("grid_layer")

    def Analysis(self, gridName):
        print("Analysis Start:")
        all_field = "count_all"
        self.CountAll(gridName, all_field)
        arcpy.OptimizedHotSpotAnalysis_stats(
            gridName, "HSAnalysis_All", all_field)
        print("All hex grids analyzed, output layer HSAnalysis_All")
        if self.districts:
            arcpy.MakeFeatureLayer_management(
                self.districts, "districts_layer")
            arcpy.MakeFeatureLayer_management(gridName, "hex_layer")
            arcpy.SelectLayerByLocation_management(
                "hex_layer", "intersect", "districts_layer")
            arcpy.OptimizedHotSpotAnalysis_stats(
                "hex_layer", "HSAnalysis_XIAN", all_field)
            print("Hex grids within Xi'an analyzed, output layer HSAnalysis_XIAN")
            with arcpy.da.SearchCursor("districts_layer", ['FID', 'Name']) as cursor:
                for row in cursor:
                    arcpy.SelectLayerByAttribute_management("districts_layer",
                                                            "NEW_SELECTION",
                                                            "FID = " + str(row[0]))
                    arcpy.SelectLayerByLocation_management(
                        "hex_layer", "intersect", "districts_layer")

                    num = int(arcpy.GetCount_management("hex_layer")[0])
                    print("In total {0} grids".format(num))
                    if num > 30:
                        arcpy.OptimizedHotSpotAnalysis_stats(
                            "hex_layer", "HSAnalysis_{0}".format(row[1]), all_field)
                        print(
                            "Hex grids within {0} analyzed, output layer HSAnalysis_{0}".format(row[1]))
                    else:
                        print("Not enough grids to analyze")

    def CountAll(self, gridName, all_field):
        arcpy.AddField_management(gridName, all_field, "FLOAT")
        expression = ""
        for field in arcpy.ListFields(gridName):
            if "_num" in field.name:
                if (field.name in self.weights):
                    expression += "!{0}! * {1} + ".format(
                        field.name, self.weights[field.name])
                else:
                    expression += "!{0}! + ".format(field.name)
        expression = expression[:-3]
        print("Weighted Expression: {0}".format(expression))
        arcpy.CalculateField_management(
            gridName, all_field, expression, "PYTHON_9.3", "")
        print("Weighted field added")


if __name__ == "__main__":
    hsanalysis = HotSpotAnalysis(
        "./poi_tables/", "poi", "hex", "./xian/xian_district.shp")
