#!/usr/bin/python -tt
# coding: utf-8

#Guillem Àvila Padró - October 2016
#Released under GNU LICENSE
#https://opensource.org/licenses/GPL-3.0

import time
import os
import sys
import json
import string
import shutil
import zipfile

def writeData(extruder, currentDefaultSpeed, currentInfillLayerInterval, currentLayerHeight, hotendLeft, hotendRight, currentPrimaryExtruder, currentInfillExtruder, currentSupportExtruder, filamentLeft, filamentRight, quality, currentFirstLayerUnderspeed, currentOutlineUnderspeed, currentSupportUnderspeed, currentFirstLayerHeightPercentage, hotendLeftTemperature, hotendRightTemperature, currentBedTemperature, dataLog):
    if extruder[0] == 'L':
        printA = "%.2f" % float(float(currentDefaultSpeed)/60*currentInfillLayerInterval*currentLayerHeight*hotendLeft['nozzleSize'])
        printB = ""
    elif extruder[0] == 'R':
        printA = ""
        printB = "%.2f" % float(float(currentDefaultSpeed)/60*currentInfillLayerInterval*currentLayerHeight*hotendRight['nozzleSize'])
    else:
        if filamentLeft['isSupportMaterial'] != filamentRight['isSupportMaterial']:
            if filamentLeft['isSupportMaterial']:
                supportMaterialLoadedLeft = float(currentSupportUnderspeed)
                supportMaterialLoadedRight = 1
            else:
                supportMaterialLoadedLeft = 1
                supportMaterialLoadedRight = float(currentSupportUnderspeed)
        else:
            supportMaterialLoadedLeft = 1
            supportMaterialLoadedRight = 1
        if hotendLeft['nozzleSize'] != hotendRight['nozzleSize']:
            if currentPrimaryExtruder == 0: 
                printA = "%.2f" % float(float(currentDefaultSpeed)/60*currentLayerHeight*hotendLeft['nozzleSize']*supportMaterialLoadedLeft)
                printB = "%.2f" % float(float(currentDefaultSpeed)/60*currentInfillLayerInterval*currentLayerHeight*hotendRight['nozzleSize']*supportMaterialLoadedRight)
            else:
                printA = "%.2f" % float(float(currentDefaultSpeed)/60*currentLayerHeight*currentInfillLayerInterval*hotendLeft['nozzleSize']*supportMaterialLoadedLeft)
                printB = "%.2f" % float(float(currentDefaultSpeed)/60*currentLayerHeight*hotendRight['nozzleSize']*supportMaterialLoadedRight)
        else:
            printA = "%.2f" % float(float(currentDefaultSpeed)/60*currentInfillLayerInterval*currentLayerHeight*hotendLeft['nozzleSize']*supportMaterialLoadedLeft)
            printB = "%.2f" % float(float(currentDefaultSpeed)/60*currentInfillLayerInterval*currentLayerHeight*hotendRight['nozzleSize']*supportMaterialLoadedRight)
    dataLog.append(filamentLeft['id']+";"+filamentRight['id']+";"+extruder+";"+quality['id']+";"+hotendLeft['id']+";"+hotendRight['id']+";"+'T'+str(currentInfillExtruder)+";"+'T'+str(currentPrimaryExtruder)+";"+'T'+str(currentSupportExtruder)+";"+str(printA)+";"+str(printB)+";"+str(currentInfillLayerInterval)+";"+str("%.2f" % float(currentDefaultSpeed/60.))+";"+str(currentFirstLayerUnderspeed)+";"+str(currentOutlineUnderspeed)+";"+str(currentSupportUnderspeed)+";"+str(currentFirstLayerHeightPercentage)+";"+str(hotendLeftTemperature)+";"+str(hotendRightTemperature)+";"+str(currentBedTemperature)+";\n")

def speedMultiplier(hotend, filament):
    if filament['isFlexibleMaterial']:
        return float(filament['defaultPrintSpeed'])/24*hotend['nozzleSize']
    else:
        return float(filament['defaultPrintSpeed'])/60

def purgeValues(hotend, filament):
    baseSpeed04 = 50
    baseStartLenght04 = 7
    baseToolChangeLenght04 = 1.5
    return str("%.2f" % float((hotend['nozzleSize']/0.4)**2*baseSpeed04)), str("%.2f" % float((hotend['nozzleSize']/0.4)**2*baseStartLenght04*filament['purgeLenght']/baseToolChangeLenght04)), str("%.2f" % float((hotend['nozzleSize']/0.4)**2*filament['purgeLenght']))

def flowValue(hotend, filament):
    if hotend['nozzleSize'] <= 0.6:
        if filament['maxFlow'] == 'None':
            return 0.4*0.2*filament['advisedMaxPrintSpeed']
        else:
            return filament['maxFlow']
    else:
        if filament['maxFlowForHighFlowHotend'] == 'None':
            if filament['maxFlow'] == 'None':
                return 0.4*0.2*filament['advisedMaxPrintSpeed']
            else:
                return filament['maxFlow']
        else:
            return filament['maxFlowForHighFlowHotend']

def temperatureValue(filament, hotend, layerHeight, speed, base = 5):
    # adaptative temperature according to flow values. Rounded to base
    flow = hotend['nozzleSize']*layerHeight*float(speed)/60
    temperature = int(base * round((filament['printTemperature'][0]+flow*float(filament['printTemperature'][1]-filament['printTemperature'][0])/flowValue(hotend, filament))/float(base)))
    return temperature

def speedValues(hotendLeft, hotendRight, filamentLeft, filamentRight, quality, action):
    if action == 'MEX Left' or action == 'IDEX, Infill with Right' or action == 'IDEX, Supports with Right':
        currentFilament = filamentLeft
        leftExtruderDefaultSpeed = quality['defaultSpeed']*speedMultiplier(hotendLeft, filamentLeft)
        leftExtruderMaxSpeedAtDefaultTemperature = flowValue(hotendLeft, filamentLeft)/(hotendLeft['nozzleSize']*quality['layerHeightMultiplier']*hotendLeft['nozzleSize'])
        if action == 'IDEX, Infill with Right':
            rightExtruderMaxSpeedAtHighTemperature = flowValue(hotendRight, filamentRight)/(hotendRight['nozzleSize']*quality['layerHeightMultiplier']*hotendRight['nozzleSize'])
            currentDefaultSpeed = int(str(float(min(leftExtruderDefaultSpeed, leftExtruderMaxSpeedAtDefaultTemperature, rightExtruderMaxSpeedAtHighTemperature)*60)).split('.')[0])
        else:
            currentDefaultSpeed = int(str(float(min(leftExtruderDefaultSpeed, leftExtruderMaxSpeedAtDefaultTemperature)*60)).split('.')[0])
        leftExtruderNeededFirstLayerUnderspeed = leftExtruderDefaultSpeed*60*quality['firstLayerUnderspeed']/float(currentDefaultSpeed) 
        leftExtruderNeededOutlineUnderspeed = leftExtruderDefaultSpeed*60*quality['outlineUnderspeed']/float(currentDefaultSpeed)
        leftExtruderNeededSupportUnderspeed = leftExtruderDefaultSpeed*60*0.9/float(currentDefaultSpeed)
        if filamentLeft['isFlexibleMaterial']:
            currentFirstLayerUnderspeed = 1.00
            currentOutlineUnderspeed = 1.00
        else:
            currentFirstLayerUnderspeed = "%.2f" % float(min(leftExtruderNeededFirstLayerUnderspeed, 1))
            currentOutlineUnderspeed = "%.2f" % float(min(leftExtruderNeededOutlineUnderspeed, 1))

        if action == 'IDEX, Supports with Right':
            currentSupportUnderspeed = "%.2f" % float(flowValue(hotendRight, filamentRight)/float(hotendLeft['nozzleSize'] * quality['layerHeightMultiplier']*hotendRight['nozzleSize']*currentDefaultSpeed/60.))
        else:
            currentSupportUnderspeed = "%.2f" % float(min(leftExtruderNeededSupportUnderspeed, 1))
    elif action == 'MEX Right' or action == 'IDEX, Infill with Left' or action == 'IDEX, Supports with Left':
        currentFilament = filamentRight
        rightExtruderDefaultSpeed = quality['defaultSpeed']*speedMultiplier(hotendRight, filamentRight)
        rightExtruderMaxSpeedAtDefaultTemperature = flowValue(hotendRight, filamentRight)/(hotendRight['nozzleSize']*quality['layerHeightMultiplier']*hotendRight['nozzleSize'])
        if action == 'IDEX, Infill with Left':
            leftExtruderMaxSpeedAtHighTemperature = flowValue(hotendLeft, filamentLeft)/(hotendLeft['nozzleSize']*quality['layerHeightMultiplier']*hotendLeft['nozzleSize'])
            currentDefaultSpeed = int(str(float(min(rightExtruderDefaultSpeed, rightExtruderMaxSpeedAtDefaultTemperature, leftExtruderMaxSpeedAtHighTemperature)*60)).split('.')[0])
        else:
            currentDefaultSpeed = int(str(float(min(rightExtruderDefaultSpeed, rightExtruderMaxSpeedAtDefaultTemperature)*60)).split('.')[0])
        rightExtruderNeededFirstLayerUnderspeed = rightExtruderDefaultSpeed*60*quality['firstLayerUnderspeed']/float(currentDefaultSpeed)
        rightExtruderNeededOutlineUnderspeed = rightExtruderDefaultSpeed*60*quality['outlineUnderspeed']/float(currentDefaultSpeed)
        rightExtruderNeededSupportUnderspeed = rightExtruderDefaultSpeed*60*0.9/float(currentDefaultSpeed)
        if filamentRight['isFlexibleMaterial']:
            currentFirstLayerUnderspeed = 1.00
            currentOutlineUnderspeed = 1.00
        else:
            currentFirstLayerUnderspeed = "%.2f" % float(min(rightExtruderNeededFirstLayerUnderspeed, 1))
            currentOutlineUnderspeed = "%.2f" % float(min(rightExtruderNeededOutlineUnderspeed, 1))
        if action == 'IDEX, Supports with Left':
            currentSupportUnderspeed = "%.2f" % float(flowValue(hotendLeft, filamentLeft)/float(hotendRight['nozzleSize']*quality['layerHeightMultiplier']*hotendLeft['nozzleSize']*currentDefaultSpeed/60.))
        else:
            currentSupportUnderspeed = "%.2f" % float(min(rightExtruderNeededSupportUnderspeed, 1))
    if currentFilament['isFlexibleMaterial']:
        currentFirstLayerUnderspeed = 1.00
        currentOutlineUnderspeed = 1.00
    return currentDefaultSpeed, currentFirstLayerUnderspeed, currentOutlineUnderspeed, currentSupportUnderspeed

def createSimplify3DProfile(hotendLeft, hotendRight, filamentLeft, filamentRight, dataLog, createFile):
    fff = []
    fff.append(r'<?xml version="1.0" encoding="utf-8"?>'+"\n")
    for q in profilesData['quality']:
        if q['id'] == 'Medium':
            defaultPrintQualityBase = 'Medium'
            break
        else:
            defaultPrintQualityBase = profilesData['quality'][0]['id']
    if hotendLeft['id'] == 'None':
        if hotendRight['id'] == 'None':
            return
        else:            
            fileName = "BCN3D Sigma - Right Extruder "+str(hotendRight['nozzleSize'])+" Only ("+filamentRight['id']+")"
            defaultPrintQuality = 'Right Extruder - '+defaultPrintQualityBase
            extruderPrintOptions = ["Right Extruder"]
            filamentLeft = dict([('id', '')])
    elif hotendRight['id'] == 'None':
        fileName = "BCN3D Sigma - Left Extruder "+str(hotendLeft['nozzleSize'])+" Only ("+filamentLeft['id']+")"
        defaultPrintQuality = 'Left Extruder - '+defaultPrintQualityBase
        extruderPrintOptions = ["Left Extruder"]
        filamentRight = dict([('id', '')])
    else:
        fileName = "BCN3D Sigma - "+str(hotendLeft['nozzleSize'])+" Left ("+filamentLeft['id']+"), "+str(hotendRight['nozzleSize'])+" Right ("+filamentRight['id']+")"
        defaultPrintQuality = 'Left Extruder - '+defaultPrintQualityBase
        extruderPrintOptions = ["Left Extruder", "Right Extruder", "Both Extruders"]    
    fff.append(r'<profile name="'+fileName+r'" version="'+time.strftime("%Y-%m-%d")+" "+time.strftime("%H:%M:%S")+r'" app="S3D-Software 3.1.1">'+"\n")    
    fff.append(r'  <baseProfile></baseProfile>'+"\n")
    fff.append(r'  <printMaterial></printMaterial>'+"\n")
    fff.append(r'  <printQuality>'+defaultPrintQuality+'</printQuality>'+"\n") #+extruder+secondaryExtruderAction+str(quality['id'])+
    if hotendRight['id'] != 'None':
        fff.append(r'  <printExtruders>Left Extruder Only</printExtruders>'+"\n")
    else:
        fff.append(r'  <printExtruders>Right Extruder Only</printExtruders>'+"\n")
    if hotendLeft['id'] != 'None':
        fff.append(r'  <extruder name="Left Extruder '+str(hotendLeft['nozzleSize'])+r'">'+"\n")
        fff.append(r'    <toolheadNumber>0</toolheadNumber>'+"\n")
        fff.append(r'    <diameter>'+str(hotendLeft['nozzleSize'])+r'</diameter>'+"\n")
        fff.append(r'    <autoWidth>0</autoWidth>'+"\n")
        fff.append(r'    <width>'+str(hotendLeft['nozzleSize'])+r'</width>'+"\n")
        fff.append(r'    <extrusionMultiplier>'+str(filamentLeft['extrusionMultiplier'])+r'</extrusionMultiplier>'+"\n")
        fff.append(r'    <useRetract>1</useRetract>'+"\n")
        fff.append(r'    <retractionDistance>'+str(filamentLeft['retractionDistance'])+r'</retractionDistance>'+"\n")
        fff.append(r'    <extraRestartDistance>0</extraRestartDistance>'+"\n")
        fff.append(r'    <retractionZLift>0.05</retractionZLift>'+"\n")
        fff.append(r'    <retractionSpeed>'+str(filamentLeft['retractionSpeed']*60)+r'</retractionSpeed>'+"\n")
        fff.append(r'    <useCoasting>0</useCoasting>'+"\n")
        fff.append(r'    <coastingDistance>0.2</coastingDistance>'+"\n")
        fff.append(r'    <useWipe>1</useWipe>'+"\n")
        fff.append(r'    <wipeDistance>5</wipeDistance>'+"\n")
        fff.append(r'  </extruder>'+"\n")
    if hotendRight['id'] != 'None':
        fff.append(r'  <extruder name="Right Extruder '+str(hotendRight['nozzleSize'])+r'">'+"\n")
        fff.append(r'    <toolheadNumber>1</toolheadNumber>'+"\n")
        fff.append(r'    <diameter>'+str(hotendRight['nozzleSize'])+r'</diameter>'+"\n")
        fff.append(r'    <autoWidth>0</autoWidth>'+"\n")
        fff.append(r'    <width>'+str(hotendRight['nozzleSize'])+r'</width>'+"\n")
        fff.append(r'    <extrusionMultiplier>'+str(filamentRight['extrusionMultiplier'])+r'</extrusionMultiplier>'+"\n")
        fff.append(r'    <useRetract>1</useRetract>'+"\n")
        fff.append(r'    <retractionDistance>'+str(filamentRight['retractionDistance'])+r'</retractionDistance>'+"\n")
        fff.append(r'    <extraRestartDistance>0</extraRestartDistance>'+"\n")
        fff.append(r'    <retractionZLift>0.05</retractionZLift>'+"\n")
        fff.append(r'    <retractionSpeed>'+str(filamentRight['retractionSpeed']*60)+r'</retractionSpeed>'+"\n")
        fff.append(r'    <useCoasting>0</useCoasting>'+"\n")
        fff.append(r'    <coastingDistance>0.2</coastingDistance>'+"\n")
        fff.append(r'    <useWipe>1</useWipe>'+"\n")
        fff.append(r'    <wipeDistance>5</wipeDistance>'+"\n")
        fff.append(r'  </extruder>'+"\n")
    fff.append(r'  <primaryExtruder>0</primaryExtruder>'+"\n")
    fff.append(r'  <layerHeight>0.2</layerHeight>'+"\n")
    fff.append(r'  <topSolidLayers>4</topSolidLayers>'+"\n")
    fff.append(r'  <bottomSolidLayers>4</bottomSolidLayers>'+"\n")
    fff.append(r'  <perimeterOutlines>3</perimeterOutlines>'+"\n")
    fff.append(r'  <printPerimetersInsideOut>1</printPerimetersInsideOut>'+"\n")
    fff.append(r'  <startPointOption>2</startPointOption>'+"\n")
    fff.append(r'  <startPointOriginX>0</startPointOriginX>'+"\n")
    fff.append(r'  <startPointOriginY>0</startPointOriginY>'+"\n")
    fff.append(r'  <startPointOriginZ>300</startPointOriginZ>'+"\n")
    fff.append(r'  <sequentialIslands>0</sequentialIslands>'+"\n")
    fff.append(r'  <spiralVaseMode>0</spiralVaseMode>'+"\n")
    fff.append(r'  <firstLayerHeightPercentage>125</firstLayerHeightPercentage>'+"\n")
    fff.append(r'  <firstLayerWidthPercentage>100</firstLayerWidthPercentage>'+"\n")
    fff.append(r'  <firstLayerUnderspeed>0.85</firstLayerUnderspeed>'+"\n")
    fff.append(r'  <useRaft>0</useRaft>'+"\n")
    fff.append(r'  <raftExtruder>0</raftExtruder>'+"\n")
    fff.append(r'  <raftLayers>2</raftLayers>'+"\n")
    fff.append(r'  <raftOffset>3</raftOffset>'+"\n")
    fff.append(r'  <raftSeparationDistance>0.1</raftSeparationDistance>'+"\n")
    fff.append(r'  <raftInfill>85</raftInfill>'+"\n")
    fff.append(r'  <disableRaftBaseLayers>0</disableRaftBaseLayers>'+"\n")
    fff.append(r'  <useSkirt>1</useSkirt>'+"\n")
    fff.append(r'  <skirtExtruder>999</skirtExtruder>'+"\n")
    fff.append(r'  <skirtLayers>1</skirtLayers>'+"\n")
    fff.append(r'  <skirtOutlines>2</skirtOutlines>'+"\n")
    fff.append(r'  <skirtOffset>4</skirtOffset>'+"\n")
    fff.append(r'  <usePrimePillar>0</usePrimePillar>'+"\n")
    fff.append(r'  <primePillarExtruder>999</primePillarExtruder>'+"\n")
    fff.append(r'  <primePillarWidth>15</primePillarWidth>'+"\n")
    fff.append(r'  <primePillarLocation>7</primePillarLocation>'+"\n")
    fff.append(r'  <primePillarSpeedMultiplier>1</primePillarSpeedMultiplier>'+"\n")
    fff.append(r'  <useOozeShield>0</useOozeShield>'+"\n")
    fff.append(r'  <oozeShieldExtruder>999</oozeShieldExtruder>'+"\n")
    fff.append(r'  <oozeShieldOffset>2</oozeShieldOffset>'+"\n")
    fff.append(r'  <oozeShieldOutlines>1</oozeShieldOutlines>'+"\n")
    fff.append(r'  <oozeShieldSidewallShape>1</oozeShieldSidewallShape>'+"\n")
    fff.append(r'  <oozeShieldSidewallAngle>30</oozeShieldSidewallAngle>'+"\n")
    fff.append(r'  <oozeShieldSpeedMultiplier>1</oozeShieldSpeedMultiplier>'+"\n")
    fff.append(r'  <infillExtruder>1</infillExtruder>'+"\n")
    fff.append(r'  <internalInfillPattern>Rectilinear</internalInfillPattern>'+"\n")
    fff.append(r'  <externalInfillPattern>Rectilinear</externalInfillPattern>'+"\n")
    fff.append(r'  <infillPercentage>20</infillPercentage>'+"\n")
    fff.append(r'  <outlineOverlapPercentage>25</outlineOverlapPercentage>'+"\n")
    fff.append(r'  <infillExtrusionWidthPercentage>100</infillExtrusionWidthPercentage>'+"\n")
    fff.append(r'  <minInfillLength>3</minInfillLength>'+"\n")
    fff.append(r'  <infillLayerInterval>1</infillLayerInterval>'+"\n")
    fff.append(r'  <infillAngles>45,-45</infillAngles>'+"\n")
    fff.append(r'  <overlapInfillAngles>0</overlapInfillAngles>'+"\n")
    fff.append(r'  <generateSupport>0</generateSupport>'+"\n")
    fff.append(r'  <supportExtruder>0</supportExtruder>'+"\n")
    fff.append(r'  <supportInfillPercentage>25</supportInfillPercentage>'+"\n")
    fff.append(r'  <supportExtraInflation>0</supportExtraInflation>'+"\n")
    fff.append(r'  <denseSupportLayers>5</denseSupportLayers>'+"\n")
    fff.append(r'  <denseSupportInfillPercentage>75</denseSupportInfillPercentage>'+"\n")
    fff.append(r'  <supportLayerInterval>1</supportLayerInterval>'+"\n")
    fff.append(r'  <supportHorizontalPartOffset>0.2</supportHorizontalPartOffset>'+"\n")
    fff.append(r'  <supportUpperSeparationLayers>1</supportUpperSeparationLayers>'+"\n")
    fff.append(r'  <supportLowerSeparationLayers>1</supportLowerSeparationLayers>'+"\n")
    fff.append(r'  <supportType>0</supportType>'+"\n")
    fff.append(r'  <supportGridSpacing>3</supportGridSpacing>'+"\n")
    fff.append(r'  <maxOverhangAngle>45</maxOverhangAngle>'+"\n")
    fff.append(r'  <supportAngles>0</supportAngles>'+"\n")
    if hotendLeft['id'] != 'None':
        fff.append(r'  <temperatureController name="Left Extruder '+str(hotendLeft['nozzleSize'])+r'">'+"\n")
        fff.append(r'    <temperatureNumber>0</temperatureNumber>'+"\n")
        fff.append(r'    <isHeatedBed>0</isHeatedBed>'+"\n")
        fff.append(r'    <relayBetweenLayers>0</relayBetweenLayers>'+"\n")
        fff.append(r'    <relayBetweenLoops>0</relayBetweenLoops>'+"\n")
        # fff.append(r'    <stabilizeAtStartup>1</stabilizeAtStartup>'+"\n")
        fff.append(r'    <setpoint layer="1" temperature="150"/>'+"\n")
        fff.append(r'  </temperatureController>'+"\n")
    if hotendRight['id'] != 'None':
        fff.append(r'  <temperatureController name="Right Extruder '+str(hotendRight['nozzleSize'])+r'">'+"\n")
        fff.append(r'    <temperatureNumber>1</temperatureNumber>'+"\n")
        fff.append(r'    <isHeatedBed>0</isHeatedBed>'+"\n")
        fff.append(r'    <relayBetweenLayers>0</relayBetweenLayers>'+"\n")
        fff.append(r'    <relayBetweenLoops>0</relayBetweenLoops>'+"\n")
        # fff.append(r'    <stabilizeAtStartup>1</stabilizeAtStartup>'+"\n")
        fff.append(r'    <setpoint layer="1" temperature="150"/>'+"\n")
        fff.append(r'  </temperatureController>'+"\n")
    if (hotendLeft['id'] != 'None' and filamentLeft['bedTemperature'] > 0) or (hotendRight['id'] != 'None' and filamentRight['bedTemperature'] > 0):
        fff.append(r'  <temperatureController name="Heated Bed">'+"\n")
        fff.append(r'    <temperatureNumber>0</temperatureNumber>'+"\n")
        fff.append(r'    <isHeatedBed>1</isHeatedBed>'+"\n")
        fff.append(r'    <relayBetweenLayers>0</relayBetweenLayers>'+"\n")
        fff.append(r'    <relayBetweenLoops>0</relayBetweenLoops>'+"\n")
        # fff.append(r'    <stabilizeAtStartup>1</stabilizeAtStartup>'+"\n")
        fff.append(r'    <setpoint layer="1" temperature="50"/>'+"\n")
        fff.append(r'  </temperatureController>'+"\n")
    fff.append(r'  <fanSpeed>'+"\n")
    fff.append(r'    <setpoint layer="1" speed="0" />'+"\n")
    fff.append(r'    <setpoint layer="2" speed="100"/>'+"\n")
    fff.append(r'  </fanSpeed>'+"\n")
    fff.append(r'  <blipFanToFullPower>0</blipFanToFullPower>'+"\n")
    fff.append(r'  <adjustSpeedForCooling>1</adjustSpeedForCooling>'+"\n")
    fff.append(r'  <minSpeedLayerTime>5</minSpeedLayerTime>'+"\n")
    fff.append(r'  <minCoolingSpeedSlowdown>20</minCoolingSpeedSlowdown>'+"\n")
    fff.append(r'  <increaseFanForCooling>0</increaseFanForCooling>'+"\n")
    fff.append(r'  <minFanLayerTime>45</minFanLayerTime>'+"\n")
    fff.append(r'  <maxCoolingFanSpeed>100</maxCoolingFanSpeed>'+"\n")
    fff.append(r'  <increaseFanForBridging>0</increaseFanForBridging>'+"\n")
    fff.append(r'  <bridgingFanSpeed>100</bridgingFanSpeed>'+"\n")
    fff.append(r'  <use5D>1</use5D>'+"\n")
    fff.append(r'  <relativeEdistances>0</relativeEdistances>'+"\n")
    fff.append(r'  <allowEaxisZeroing>1</allowEaxisZeroing>'+"\n")
    fff.append(r'  <independentExtruderAxes>0</independentExtruderAxes>'+"\n")
    fff.append(r'  <includeM10123>0</includeM10123>'+"\n")
    fff.append(r'  <stickySupport>1</stickySupport>'+"\n")
    fff.append(r'  <applyToolheadOffsets>0</applyToolheadOffsets>'+"\n")
    fff.append(r'  <gcodeXoffset>0</gcodeXoffset>'+"\n")
    fff.append(r'  <gcodeYoffset>0</gcodeYoffset>'+"\n")
    fff.append(r'  <gcodeZoffset>0</gcodeZoffset>'+"\n")
    fff.append(r'  <overrideMachineDefinition>1</overrideMachineDefinition>'+"\n")
    fff.append(r'  <machineTypeOverride>0</machineTypeOverride>'+"\n")
    fff.append(r'  <strokeXoverride>210</strokeXoverride>'+"\n")
    fff.append(r'  <strokeYoverride>297</strokeYoverride>'+"\n")
    fff.append(r'  <strokeZoverride>210</strokeZoverride>'+"\n")
    fff.append(r'  <originOffsetXoverride>0</originOffsetXoverride>'+"\n")
    fff.append(r'  <originOffsetYoverride>0</originOffsetYoverride>'+"\n")
    fff.append(r'  <originOffsetZoverride>0</originOffsetZoverride>'+"\n")
    fff.append(r'  <homeXdirOverride>-1</homeXdirOverride>'+"\n")
    fff.append(r'  <homeYdirOverride>-1</homeYdirOverride>'+"\n")
    fff.append(r'  <homeZdirOverride>-1</homeZdirOverride>'+"\n")
    fff.append(r'  <flipXoverride>1</flipXoverride>'+"\n")
    fff.append(r'  <flipYoverride>-1</flipYoverride>'+"\n")
    fff.append(r'  <flipZoverride>1</flipZoverride>'+"\n")
    fff.append(r'  <toolheadOffsets>0,0|0,0|0,0|0,0|0,0|0,0</toolheadOffsets>'+"\n")
    fff.append(r'  <overrideFirmwareConfiguration>1</overrideFirmwareConfiguration>'+"\n")
    fff.append(r'  <firmwareTypeOverride>RepRap (Marlin/Repetier/Sprinter)</firmwareTypeOverride>'+"\n")
    fff.append(r'  <GPXconfigOverride>r2</GPXconfigOverride>'+"\n")
    fff.append(r'  <baudRateOverride>250000</baudRateOverride>'+"\n")
    fff.append(r'  <overridePrinterModels>0</overridePrinterModels>'+"\n")
    fff.append(r'  <printerModelsOverride></printerModelsOverride>'+"\n")
    fff.append(r'  <startingGcode></startingGcode>'+"\n")
    fff.append(r'  <layerChangeGcode></layerChangeGcode>'+"\n")
    fff.append(r'  <retractionGcode></retractionGcode>'+"\n")
    fff.append(r'  <toolChangeGcode></toolChangeGcode>'+"\n")
    fff.append(r'  <endingGcode>M104 S0 T0,M104 S0 T1,M140 S0'+"\t\t"+r';heated bed heater off (if you have it),G91'+"\t\t"+r';relative positioning,G1 Y+10 F[travel_speed]'+"\t"+r';move Z up a bit and retract filament even more,G28 X0 Y0'+"\t\t"+r';move X/Y to min endstops so the head is out of the way,M84'+"\t\t"+r';steppers off,G90'+"\t\t"+r';absolute positioning,</endingGcode>'+"\n")
    fff.append(r'  <exportFileFormat>gcode</exportFileFormat>'+"\n")
    fff.append(r'  <celebration>0</celebration>'+"\n")
    fff.append(r'  <celebrationSong></celebrationSong>'+"\n")
    fff.append(r'  <postProcessing></postProcessing>'+"\n")
    fff.append(r'  <defaultSpeed>2400</defaultSpeed>'+"\n")
    fff.append(r'  <outlineUnderspeed>0.85</outlineUnderspeed>'+"\n")
    fff.append(r'  <solidInfillUnderspeed>0.85</solidInfillUnderspeed>'+"\n")
    fff.append(r'  <supportUnderspeed>0.9</supportUnderspeed>'+"\n")
    fff.append(r'  <rapidXYspeed>12000</rapidXYspeed>'+"\n")
    fff.append(r'  <rapidZspeed>1002</rapidZspeed>'+"\n")
    fff.append(r'  <minBridgingArea>50</minBridgingArea>'+"\n")
    fff.append(r'  <bridgingExtraInflation>0</bridgingExtraInflation>'+"\n")
    fff.append(r'  <bridgingExtrusionMultiplier>1</bridgingExtrusionMultiplier>'+"\n")
    fff.append(r'  <bridgingSpeedMultiplier>1</bridgingSpeedMultiplier>'+"\n")
    fff.append(r'  <filamentDiameter>2.85</filamentDiameter>'+"\n")
    fff.append(r'  <filamentPricePerKg>19.95</filamentPricePerKg>'+"\n")
    fff.append(r'  <filamentDensity>1.25</filamentDensity>'+"\n")
    fff.append(r'  <useMinPrintHeight>0</useMinPrintHeight>'+"\n")
    fff.append(r'  <minPrintHeight>0</minPrintHeight>'+"\n")
    fff.append(r'  <useMaxPrintHeight>0</useMaxPrintHeight>'+"\n")
    fff.append(r'  <maxPrintHeight>0</maxPrintHeight>'+"\n")
    fff.append(r'  <useDiaphragm>0</useDiaphragm>'+"\n")
    fff.append(r'  <diaphragmLayerInterval>5</diaphragmLayerInterval>'+"\n")
    fff.append(r'  <robustSlicing>1</robustSlicing>'+"\n")
    fff.append(r'  <mergeAllIntoSolid>0</mergeAllIntoSolid>'+"\n")
    fff.append(r'  <onlyRetractWhenCrossingOutline>1</onlyRetractWhenCrossingOutline>'+"\n")
    fff.append(r'  <retractBetweenLayers>0</retractBetweenLayers>'+"\n")
    fff.append(r'  <useRetractionMinTravel>1</useRetractionMinTravel>'+"\n")
    fff.append(r'  <retractionMinTravel>1.5</retractionMinTravel>'+"\n")
    fff.append(r'  <retractWhileWiping>1</retractWhileWiping>'+"\n")
    fff.append(r'  <onlyWipeOutlines>1</onlyWipeOutlines>'+"\n")
    fff.append(r'  <avoidCrossingOutline>1</avoidCrossingOutline>'+"\n")
    fff.append(r'  <maxMovementDetourFactor>3</maxMovementDetourFactor>'+"\n")
    fff.append(r'  <toolChangeRetractionDistance>8</toolChangeRetractionDistance>'+"\n")
    fff.append(r'  <toolChangeExtraRestartDistance>0</toolChangeExtraRestartDistance>'+"\n")
    fff.append(r'  <toolChangeRetractionSpeed>2400</toolChangeRetractionSpeed>'+"\n")
    fff.append(r'  <allowThinWallGapFill>1</allowThinWallGapFill>'+"\n")
    fff.append(r'  <thinWallAllowedOverlapPercentage>10</thinWallAllowedOverlapPercentage>'+"\n")
    fff.append(r'  <horizontalSizeCompensation>0</horizontalSizeCompensation>'+"\n")
    # fff.append(r'  <overridePrinterModels>1</overridePrinterModels>'+"\n")
    # fff.append(r'  <printerModelsOverride>BCN3DSigma.stl</printerModelsOverride>'+"\n")
    # fff.append(r'  <autoConfigureMaterial name="'+str(filamentLeft)+" Left, "+str(filamentRight)+" Right"+r'">'+"\n")
    for extruder in extruderPrintOptions:
        for quality in sorted(profilesData['quality'], key=lambda k: k['index']):
            currentInfillLayerInterval = 1
            currentGenerateSupport = 0
            currentAvoidCrossingOutline = 1
            fanActionOnToolChange1 = ''
            fanActionOnToolChange2 = ''
            # hotendLeftStabilize = 1
            # hotendRightStabilize = 1
            # MEX
            if extruder[0] == 'L' or extruder[0] == 'R':
                if extruder[0] == 'L':
                    currentPrimaryExtruder = 0
                    currentFilament = filamentLeft
                    currentHotend = hotendLeft
                    currentLayerHeight = currentHotend['nozzleSize'] * quality['layerHeightMultiplier']
                    currentDefaultSpeed, currentFirstLayerUnderspeed, currentOutlineUnderspeed, currentSupportUnderspeed = speedValues(hotendLeft, hotendRight, filamentLeft, filamentRight, quality, 'MEX Left')
                    hotendLeftTemperature = temperatureValue(filamentLeft, hotendLeft, currentLayerHeight, currentDefaultSpeed)
                    if hotendRight['id'] != 'None':
                        hotendRightTemperature = temperatureValue(filamentRight, hotendRight, currentLayerHeight, currentDefaultSpeed)
                        hotendRightStabilize = 0
                    else:
                        hotendRightTemperature = hotendLeftTemperature
                else:
                    currentPrimaryExtruder = 1
                    currentFilament = filamentRight
                    currentHotend = hotendRight
                    currentLayerHeight = currentHotend['nozzleSize'] * quality['layerHeightMultiplier']
                    currentDefaultSpeed, currentFirstLayerUnderspeed, currentOutlineUnderspeed, currentSupportUnderspeed = speedValues(hotendLeft, hotendRight, filamentLeft, filamentRight, quality, 'MEX Right')
                    hotendRightTemperature = temperatureValue(filamentRight, hotendRight, currentLayerHeight, currentDefaultSpeed)
                    if hotendLeft['id'] != 'None':
                        hotendLeftTemperature = temperatureValue(filamentLeft, hotendLeft, currentLayerHeight, currentDefaultSpeed)
                        hotendLeftStabilize = 0
                    else:
                        hotendLeftTemperature = hotendRightTemperature
                currentInfillExtruder = currentPrimaryExtruder
                currentSupportExtruder = currentPrimaryExtruder
                currentBedTemperature = currentFilament['bedTemperature']
                if filamentLeft['id'] != filamentRight['id']:
                    secondaryExtruderAction = ' ('+currentFilament['id']+') - '
                else:
                    secondaryExtruderAction = ' - '
            # IDEX
            else:
                # IDEX, Support Material
                if filamentLeft['isSupportMaterial'] != filamentRight['isSupportMaterial']:
                    currentGenerateSupport = 1
                    if filamentLeft['isSupportMaterial']:
                        currentPrimaryExtruder = 1
                        currentFilament = filamentRight
                        currentHotend = hotendRight
                        supportFilament = filamentLeft
                        supportHotend = hotendLeft
                        fanActionOnToolChange1 = '{IF NEWTOOL=0} M107'+"\t\t"+r';disable fan for support material,'
                        fanActionOnToolChange2 = '{IF NEWTOOL=1} M106'+"\t\t"+r';enable fan for part material,'
                        secondaryExtruderAction = ' (Left Ext. for supports) - '
                        currentDefaultSpeed, currentFirstLayerUnderspeed, currentOutlineUnderspeed, currentSupportUnderspeed = speedValues(hotendLeft, hotendRight, filamentLeft, filamentRight, quality, 'IDEX, Supports with Left')
                    else:
                        currentPrimaryExtruder = 0
                        currentFilament = filamentLeft
                        currentHotend = hotendLeft
                        supportFilament = filamentRight
                        supportHotend = hotendRight
                        fanActionOnToolChange1 = '{IF NEWTOOL=0} M106'+"\t\t"+r';enable fan for part material,'
                        fanActionOnToolChange2 = '{IF NEWTOOL=1} M107'+"\t\t"+r';disable fan for support material,' 
                        secondaryExtruderAction = ' (Right Ext. for supports) - '
                        currentDefaultSpeed, currentFirstLayerUnderspeed, currentOutlineUnderspeed, currentSupportUnderspeed = speedValues(hotendLeft, hotendRight, filamentLeft, filamentRight, quality, 'IDEX, Supports with Right')
                    currentInfillExtruder = currentPrimaryExtruder
                    currentSupportExtruder = abs(currentPrimaryExtruder-1)
                    currentLayerHeight = currentHotend['nozzleSize'] * quality['layerHeightMultiplier']
                    hotendLeftTemperature = temperatureValue(filamentLeft, hotendLeft, currentLayerHeight, currentDefaultSpeed)
                    hotendRightTemperature = temperatureValue(filamentRight, hotendRight, currentLayerHeight, currentDefaultSpeed)
                # IDEX, Combined Infill
                else:
                    currentAvoidCrossingOutline = 0
                    if hotendLeft['nozzleSize'] <= hotendRight['nozzleSize']:
                        currentPrimaryExtruder = 0
                        currentFilament = filamentLeft
                        currentHotend = hotendLeft
                        currentDefaultSpeed, currentFirstLayerUnderspeed, currentOutlineUnderspeed, currentSupportUnderspeed = speedValues(hotendLeft, hotendRight, filamentLeft, filamentRight, quality, 'IDEX, Infill with Right')
                        if hotendLeft['nozzleSize'] != hotendRight['nozzleSize']:
                            currentInfillLayerInterval = int(str(min(flowValue(hotendRight, filamentRight)/(max(hotendLeft['nozzleSize'], hotendRight['nozzleSize'])*currentDefaultSpeed/60*quality['layerHeightMultiplier']*min(hotendLeft['nozzleSize'], hotendRight['nozzleSize'])),(max(hotendLeft['nozzleSize'], hotendRight['nozzleSize'])*0.75)/(quality['layerHeightMultiplier']*min(hotendLeft['nozzleSize'], hotendRight['nozzleSize'])))).split('.')[0])
                        currentLayerHeight = currentHotend['nozzleSize'] * quality['layerHeightMultiplier']
                        hotendLeftTemperature = temperatureValue(filamentLeft, hotendLeft, currentLayerHeight, currentDefaultSpeed)
                        hotendRightTemperature = temperatureValue(filamentRight, hotendRight, currentLayerHeight*currentInfillLayerInterval, currentDefaultSpeed)
                        secondaryExtruderAction = ' (Right Ext. for infill) - '
                        if currentFilament['fanPercentage'] != 0:
                            fanActionOnToolChange1 = '' # '{IF NEWTOOL=0} M106'+"\t\t"+r';enable fan for perimeters,'
                            fanActionOnToolChange2 = '' # '{IF NEWTOOL=1} M107'+"\t\t"+r';disable fan for infill,'
                        if hotendLeft['nozzleSize'] == hotendRight['nozzleSize']:
                            hotendRightTemperature = temperatureValue(filamentRight, hotendRight, currentLayerHeight, currentDefaultSpeed)
                    else:
                        currentPrimaryExtruder = 1
                        currentFilament = filamentRight
                        currentHotend = hotendRight
                        currentLayerHeight = currentHotend['nozzleSize'] * quality['layerHeightMultiplier']
                        currentDefaultSpeed, currentFirstLayerUnderspeed, currentOutlineUnderspeed, currentSupportUnderspeed = speedValues(hotendLeft, hotendRight, filamentLeft, filamentRight, quality, 'IDEX, Infill with Left')
                        currentInfillLayerInterval = int(str(min(flowValue(hotendLeft, filamentLeft)/(max(hotendLeft['nozzleSize'], hotendRight['nozzleSize'])*currentDefaultSpeed/60*quality['layerHeightMultiplier']*min(hotendLeft['nozzleSize'], hotendRight['nozzleSize'])),(max(hotendLeft['nozzleSize'], hotendRight['nozzleSize'])*0.75)/(quality['layerHeightMultiplier']*min(hotendLeft['nozzleSize'], hotendRight['nozzleSize'])))).split('.')[0])
                        hotendLeftTemperature = temperatureValue(filamentLeft, hotendLeft, currentLayerHeight*currentInfillLayerInterval, currentDefaultSpeed)
                        hotendRightTemperature = temperatureValue(filamentRight, hotendRight, currentLayerHeight, currentDefaultSpeed)
                        secondaryExtruderAction = ' (Left Ext. for infill) - '
                        if currentFilament['fanPercentage'] != 0:
                            fanActionOnToolChange1 = '' # '{IF NEWTOOL=0} M107'+"\t\t"+r';disable fan for infill,'
                            fanActionOnToolChange2 = '' # '{IF NEWTOOL=1} M106'+"\t\t"+r';enable fan for perimeters,'
                    currentInfillExtruder = abs(currentPrimaryExtruder-1)
                    currentSupportExtruder = currentPrimaryExtruder
                currentBedTemperature = max(filamentLeft['bedTemperature'], filamentRight['bedTemperature'])
            currentFirstLayerHeightPercentage = int(min(125, flowValue(currentHotend, currentFilament)*100/(currentHotend['nozzleSize']*currentLayerHeight*(currentDefaultSpeed/60)*float(currentFirstLayerUnderspeed))))       
            currentPerimeterOutlines = max(2, int(round(quality['wallWidth'] / currentHotend['nozzleSize']))) #2 minimum Perimeters needed
            currentTopSolidLayers = max(4, int(round(quality['topBottomWidth'] / currentLayerHeight))) #4 minimum layers needed
            currentBottomSolidLayers = currentTopSolidLayers
            currentRaftExtruder = currentPrimaryExtruder
            currentSkirtExtruder = currentPrimaryExtruder
            fff.append(r'  <autoConfigureQuality name="'+extruder+secondaryExtruderAction+str(quality['id'])+r'">'+"\n")
            fff.append(r'    <globalExtrusionMultiplier>1</globalExtrusionMultiplier>'+"\n")
            fff.append(r'    <fanSpeed>'+"\n")
            fff.append(r'      <setpoint layer="1" speed="0" />'+"\n")
            fff.append(r'      <setpoint layer="2" speed="'+str(currentFilament['fanPercentage'])+r'" />'+"\n")
            fff.append(r'    </fanSpeed>'+"\n")
            fff.append(r'    <filamentDiameter>'+str(currentFilament['filamentDiameter'])+r'</filamentDiameter>'+"\n")
            fff.append(r'    <filamentPricePerKg>'+str(currentFilament['filamentPricePerKg'])+r'</filamentPricePerKg>'+"\n")
            fff.append(r'    <filamentDensity>'+str(currentFilament['filamentDensity'])+r'</filamentDensity>'+"\n")
            if hotendLeft['id'] != 'None':
                fff.append(r'    <extruder name="Left Extruder '+str(hotendLeft['nozzleSize'])+r'">'+"\n")
                fff.append(r'      <toolheadNumber>0</toolheadNumber>'+"\n")
                fff.append(r'      <diameter>'+str(hotendLeft['nozzleSize'])+r'</diameter>'+"\n")
                fff.append(r'      <autoWidth>0</autoWidth>'+"\n")
                fff.append(r'      <width>'+str(hotendLeft['nozzleSize'])+r'</width>'+"\n")
                fff.append(r'      <extrusionMultiplier>'+str(filamentLeft['extrusionMultiplier'])+r'</extrusionMultiplier>'+"\n")
                fff.append(r'      <useRetract>1</useRetract>'+"\n")
                fff.append(r'      <retractionDistance>'+str(filamentLeft['retractionDistance'])+r'</retractionDistance>'+"\n")
                fff.append(r'      <extraRestartDistance>0</extraRestartDistance>'+"\n")
                fff.append(r'      <retractionZLift>0.05</retractionZLift>'+"\n")
                fff.append(r'      <retractionSpeed>'+str(filamentLeft['retractionSpeed']*60)+r'</retractionSpeed>'+"\n")
                fff.append(r'      <useCoasting>0</useCoasting>'+"\n")
                fff.append(r'      <coastingDistance>0.2</coastingDistance>'+"\n")
                fff.append(r'      <useWipe>1</useWipe>'+"\n")
                fff.append(r'      <wipeDistance>5</wipeDistance>'+"\n")
                fff.append(r'    </extruder>'+"\n")
            if hotendRight['id'] != 'None':
                fff.append(r'    <extruder name="Right Extruder '+str(hotendRight['nozzleSize'])+r'">'+"\n")
                fff.append(r'      <toolheadNumber>1</toolheadNumber>'+"\n")
                fff.append(r'      <diameter>'+str(hotendRight['nozzleSize'])+r'</diameter>'+"\n")
                fff.append(r'      <autoWidth>0</autoWidth>'+"\n")
                fff.append(r'      <width>'+str(hotendRight['nozzleSize'])+r'</width>'+"\n")
                fff.append(r'      <extrusionMultiplier>'+str(filamentRight['extrusionMultiplier'])+r'</extrusionMultiplier>'+"\n")
                fff.append(r'      <useRetract>1</useRetract>'+"\n")
                fff.append(r'      <retractionDistance>'+str(filamentRight['retractionDistance'])+r'</retractionDistance>'+"\n")
                fff.append(r'      <extraRestartDistance>0</extraRestartDistance>'+"\n")
                fff.append(r'      <retractionZLift>0.05</retractionZLift>'+"\n")
                fff.append(r'      <retractionSpeed>'+str(filamentRight['retractionSpeed']*60)+r'</retractionSpeed>'+"\n")
                fff.append(r'      <useCoasting>0</useCoasting>'+"\n")
                fff.append(r'      <coastingDistance>0.2</coastingDistance>'+"\n")
                fff.append(r'      <useWipe>1</useWipe>'+"\n")
                fff.append(r'      <wipeDistance>5</wipeDistance>'+"\n")
                fff.append(r'    </extruder>'+"\n")
            fff.append(r'    <primaryExtruder>'+str(currentPrimaryExtruder)+r'</primaryExtruder>'+"\n")
            fff.append(r'    <raftExtruder>'+str(currentRaftExtruder)+r'</raftExtruder>'+"\n")
            fff.append(r'    <skirtExtruder>'+str(currentSkirtExtruder)+r'</skirtExtruder>'+"\n")
            fff.append(r'    <infillExtruder>'+str(currentInfillExtruder)+r'</infillExtruder>'+"\n")
            fff.append(r'    <supportExtruder>'+str(currentSupportExtruder)+r'</supportExtruder>'+"\n")
            fff.append(r'    <generateSupport>'+str(currentGenerateSupport)+r'</generateSupport>'+"\n")
            fff.append(r'    <layerHeight>'+str(currentLayerHeight)+r'</layerHeight>'+"\n")
            fff.append(r'    <firstLayerHeightPercentage>'+str(currentFirstLayerHeightPercentage)+r'</firstLayerHeightPercentage>'+"\n")
            fff.append(r'    <topSolidLayers>'+str(currentTopSolidLayers)+r'</topSolidLayers>'+"\n")
            fff.append(r'    <bottomSolidLayers>'+str(currentBottomSolidLayers)+r'</bottomSolidLayers>'+"\n")
            fff.append(r'    <perimeterOutlines>'+str(currentPerimeterOutlines)+r'</perimeterOutlines>'+"\n")
            fff.append(r'    <infillPercentage>'+str(quality['infillPercentage'])+r'</infillPercentage>'+"\n")
            fff.append(r'    <infillLayerInterval>'+str(currentInfillLayerInterval)+r'</infillLayerInterval>'+"\n")
            fff.append(r'    <defaultSpeed>'+str(currentDefaultSpeed)+r'</defaultSpeed>'+"\n")
            fff.append(r'    <firstLayerUnderspeed>'+str(currentFirstLayerUnderspeed)+r'</firstLayerUnderspeed>'+"\n")
            fff.append(r'    <outlineUnderspeed>'+str(currentOutlineUnderspeed)+r'</outlineUnderspeed>'+"\n")
            fff.append(r'    <supportUnderspeed>'+str(currentSupportUnderspeed)+r'</supportUnderspeed>'+"\n")
            fff.append(r'    <avoidCrossingOutline>'+str(currentAvoidCrossingOutline)+'</avoidCrossingOutline>'+"\n")
            if hotendLeft['id'] != 'None':
                fff.append(r'    <temperatureController name="Left Extruder '+str(hotendLeft['nozzleSize'])+r'">'+"\n")
                fff.append(r'      <temperatureNumber>0</temperatureNumber>'+"\n")
                fff.append(r'      <isHeatedBed>0</isHeatedBed>'+"\n")
                fff.append(r'      <relayBetweenLayers>0</relayBetweenLayers>'+"\n")
                fff.append(r'      <relayBetweenLoops>0</relayBetweenLoops>'+"\n")
                # fff.append(r'      <stabilizeAtStartup>'+str(hotendLeftStabilize)+'</stabilizeAtStartup>'+"\n")
                fff.append(r'      <setpoint layer="1" temperature="'+str(hotendLeftTemperature)+r'"/>'+"\n")
                fff.append(r'    </temperatureController>'+"\n")
            if hotendRight['id'] != 'None':
                fff.append(r'    <temperatureController name="Right Extruder '+str(hotendRight['nozzleSize'])+r'">'+"\n")
                fff.append(r'      <temperatureNumber>1</temperatureNumber>'+"\n")
                fff.append(r'      <isHeatedBed>0</isHeatedBed>'+"\n")
                fff.append(r'      <relayBetweenLayers>0</relayBetweenLayers>'+"\n")
                fff.append(r'      <relayBetweenLoops>0</relayBetweenLoops>'+"\n")
                # fff.append(r'      <stabilizeAtStartup>'+str(hotendRightStabilize)+'</stabilizeAtStartup>'+"\n")
                fff.append(r'      <setpoint layer="1" temperature="'+str(hotendRightTemperature)+r'"/>'+"\n")
                fff.append(r'    </temperatureController>'+"\n")
            if (hotendLeft['id'] != 'None' and filamentLeft['bedTemperature'] > 0) or (hotendRight['id'] != 'None' and filamentRight['bedTemperature'] > 0):
                fff.append(r'    <temperatureController name="Heated Bed">'+"\n")
                fff.append(r'      <temperatureNumber>0</temperatureNumber>'+"\n")
                fff.append(r'      <isHeatedBed>1</isHeatedBed>'+"\n")
                fff.append(r'      <relayBetweenLayers>0</relayBetweenLayers>'+"\n")
                fff.append(r'      <relayBetweenLoops>0</relayBetweenLoops>'+"\n")
                # fff.append(r'      <stabilizeAtStartup>1</stabilizeAtStartup>'+"\n")
                fff.append(r'      <setpoint layer="1" temperature="'+str(currentBedTemperature)+r'"/>'+"\n")
                fff.append(r'    </temperatureController>'+"\n")
            fff.append(r'  </autoConfigureQuality>'+"\n")

            if dataLog != 'noData' :
                # Store flows, speeds, temperatures and other data
                writeData(extruder, currentDefaultSpeed, currentInfillLayerInterval, currentLayerHeight, hotendLeft, hotendRight, currentPrimaryExtruder, currentInfillExtruder, currentSupportExtruder, filamentLeft, filamentRight, quality, currentFirstLayerUnderspeed, currentOutlineUnderspeed, currentSupportUnderspeed, currentFirstLayerHeightPercentage, hotendLeftTemperature, hotendRightTemperature, currentBedTemperature, dataLog)                        

    # fff.append(r'  </autoConfigureMaterial>'+"\n")

    # toggleTemperatureControllers disabled until Simplify3D allows the option
    if hotendLeft['id'] != 'None':
        fff.append(r'  <autoConfigureExtruders name="Left Extruder Only"  allowedToolheads="1">'+"\n")
        # if hotendLeft['id'] != 'None':
        #     fff.append(r'    <toggleTemperatureController name="Left Extruder '+str(hotendLeft['nozzleSize'])+r'" status="on" stabilize="on"/>'+"\n")
        # if hotendRight['id'] != 'None':
        #     fff.append(r'    <toggleTemperatureController name="Right Extruder '+str(hotendRight['nozzleSize'])+r'" status="off" stabilize="off"/>'+"\n")
        # if (hotendLeft['id'] != 'None' and filamentLeft['bedTemperature'] > 0) or (hotendRight['id'] != 'None' and filamentRight['bedTemperature'] > 0):
        #     fff.append(r'    <toggleTemperatureController name="Heated Bed" status="on" stabilize="on"/>'+"\n")
        currentPurgeSpeed, currentStartPurgeLenght, currentToolChangePurgeLenght = purgeValues(hotendLeft, filamentLeft)
        fff.append(r'    <startingGcode>G21'+"\t\t"+r';metric values,G90'+"\t\t"+r';absolute positioning,M82'+"\t\t"+r';set extruder to absolute mode,M107'+"\t\t"+r';start with the fan off,G28 X0 Y0'+"\t\t"+r';move X/Y to min endstops,G28 Z0'+"\t\t"+r';move Z to min endstops,T0'+"\t\t"+r';change to active toolhead,G92 E0'+"\t\t"+r';zero the extruded length,G1 Z5 F200'+"\t\t"+r';Safety Z axis movement,G1 F'+currentPurgeSpeed+' E'+currentStartPurgeLenght+"\t"+r';extrude '+currentStartPurgeLenght+r'mm of feed stock,G92 E0'+"\t\t"+r';zero the extruded length again,G1 F200 E-4'+"\t\t"+r';Retract before printing,G1 F[travel_speed],</startingGcode>'+"\n")
        fff.append(r'    <toolChangeGcode/>'+"\n")
        fff.append(r'  </autoConfigureExtruders>'+"\n")
    if hotendRight['id'] != 'None':
        fff.append(r'  <autoConfigureExtruders name="Right Extruder Only"  allowedToolheads="1">'+"\n")
        # if hotendLeft['id'] != 'None':
        #     fff.append(r'    <toggleTemperatureController name="Left Extruder '+str(hotendLeft['nozzleSize'])+r'" status="off" stabilize="off"/>'+"\n")
        # if hotendRight['id'] != 'None':
        #     fff.append(r'    <toggleTemperatureController name="Right Extruder '+str(hotendRight['nozzleSize'])+r'" status="on" stabilize="on"/>'+"\n")
        # if (hotendLeft['id'] != 'None' and filamentLeft['bedTemperature'] > 0) or (hotendRight['id'] != 'None' and filamentRight['bedTemperature'] > 0):
        #     fff.append(r'    <toggleTemperatureController name="Heated Bed" status="on" stabilize="on"/>'+"\n")
        currentPurgeSpeed, currentStartPurgeLenght, currentToolChangePurgeLenght = purgeValues(hotendRight, filamentRight)
        fff.append(r'    <startingGcode>G21'+"\t\t"+r';metric values,G90'+"\t\t"+r';absolute positioning,M82'+"\t\t"+r';set extruder to absolute mode,M107'+"\t\t"+r';start with the fan off,G28 X0 Y0'+"\t\t"+r';move X/Y to min endstops,G28 Z0'+"\t\t"+r';move Z to min endstops,T1'+"\t\t"+r';change to active toolhead,G92 E0'+"\t\t"+r';zero the extruded length,G1 Z5 F200'+"\t\t"+r';Safety Z axis movement,G1 F'+currentPurgeSpeed+' E'+currentStartPurgeLenght+"\t"+r';extrude '+currentStartPurgeLenght+r'mm of feed stock,G92 E0'+"\t\t"+r';zero the extruded length again,G1 F200 E-4'+"\t\t"+r';Retract before printing,G1 F[travel_speed],</startingGcode>'+"\n")
        fff.append(r'    <toolChangeGcode/>'+"\n")
        fff.append(r'  </autoConfigureExtruders>'+"\n")
    if hotendLeft['id'] != 'None' and hotendRight['id'] != 'None':
        fff.append(r'  <autoConfigureExtruders name="Both Extruders"  allowedToolheads="2">'+"\n")
        # if hotendLeft['id'] != 'None':
        #     fff.append(r'    <toggleTemperatureController name="Left Extruder '+str(hotendLeft['nozzleSize'])+r'" status="on" stabilize="on"/>'+"\n")
        # if hotendRight['id'] != 'None':
        #     fff.append(r'    <toggleTemperatureController name="Right Extruder '+str(hotendRight['nozzleSize'])+r'" status="on" stabilize="on"/>'+"\n")
        # if (hotendLeft['id'] != 'None' and filamentLeft['bedTemperature'] > 0) or (hotendRight['id'] != 'None' and filamentRight['bedTemperature'] > 0):
        #     fff.append(r'    <toggleTemperatureController name="Heated Bed" status="on" stabilize="on"/>'+"\n")
        currentPurgeSpeedT0, currentStartPurgeLenghtT0, currentToolChangePurgeLenghtT0 = purgeValues(hotendLeft, filamentLeft)
        currentPurgeSpeedT1, currentStartPurgeLenghtT1, currentToolChangePurgeLenghtT1 = purgeValues(hotendRight, filamentRight)
        fff.append(r'    <startingGcode>G21'+"\t\t"+r';metric values,G90'+"\t\t"+r';absolute positioning,M107'+"\t\t"+r';start with the fan off,G28 X0 Y0'+"\t\t"+r';move X/Y to min endstops,G28 Z0'+"\t\t"+r';move Z to min endstops,T1'+"\t\t"+r';Switch to the 2nd extruder,G92 E0'+"\t\t"+r';zero the extruded length,G1 F'+currentPurgeSpeedT1+' E'+currentStartPurgeLenghtT1+"\t"+r';extrude '+currentStartPurgeLenghtT1+r'mm of feed stock,G92 E0'+"\t\t"+r';zero the extruded length again,G1 F200 E-9,T0'+"\t\t"+r';Switch to the first extruder,G92 E0'+"\t\t"+r';zero the extruded length,G1 F'+currentPurgeSpeedT0+' E'+currentStartPurgeLenghtT0+"\t"+r';extrude '+currentStartPurgeLenghtT0+r'mm of feed stock,G92 E0'+"\t\t"+r';zero the extruded length again,G1 Z5 F200'+"\t\t"+r';Safety Z axis movement,G1 F[travel_speed]</startingGcode>'+"\n")
        fff.append(r'    <toolChangeGcode>{IF NEWTOOL=0} T0'+"\t\t"+r';start tool switch 0,;{IF NEWTOOL=0} G1 X0 Y0 F[travel_speed]'+"\t"+r';travel,{IF NEWTOOL=0} G1 F500 E-0.5'+"\t\t"+r';fast purge,{IF NEWTOOL=0} G1 F'+currentPurgeSpeedT0+' E'+currentToolChangePurgeLenghtT0+"\t"+r';slow purge,{IF NEWTOOL=0} G92 E0'+"\t\t"+r';reset t0,{IF NEWTOOL=0} G1 F3000 E-4.5'+"\t"+r';retract,{IF NEWTOOL=0} G1 F[travel_speed]'+"\t"+r';end tool switch,'+fanActionOnToolChange1+r',{IF NEWTOOL=1} T1'+"\t\t"+r';start tool switch 1,;{IF NEWTOOL=1} G1 X210 Y0 F[travel_speed]'+"\t"+r';travel,{IF NEWTOOL=1} G1 F500 E-0.5'+"\t\t"+r';fast purge,{IF NEWTOOL=1} G1 F'+currentPurgeSpeedT1+' E'+currentToolChangePurgeLenghtT1+"\t"+r';slow purge,{IF NEWTOOL=1} T1'+"\t\t"+r';start tool switch 1,{IF NEWTOOL=1} G92 E0'+"\t\t"+r';reset t1,{IF NEWTOOL=1} G1 F3000 E-4.5'+"\t"+r';retract,{IF NEWTOOL=1} G1 F[travel_speed]'+"\t"+r';end tool switch,'+fanActionOnToolChange2+r',G91,G1 F[travel_speed] Z2,G90</toolChangeGcode>'+"\n")
        fff.append(r'  </autoConfigureExtruders>'+"\n")

    fff.append(r'</profile>'+"\n")
    if createFile == 'createFile':
        f = open(fileName+".fff", "w")
        f.writelines(fff)
        f.close()
    if createFile == 'noFile':
        print string.join(fff)
    if createFile == 'onlyFilename':
        print fileName+'.fff'
    return fileName+'.fff'

def createCuraProfile(hotend, filamentLeft, filamentRight, createFile):
    ini = []
    ini.append(r'[profile]'+"\n")
    ini.append(r'layer_height = 0.2'+"\n")
    ini.append(r'wall_thickness = 0.8'+"\n")
    ini.append(r'retraction_enable = True'+"\n")
    ini.append(r'solid_layer_thickness = 0.8'+"\n")
    ini.append(r'fill_density = 15'+"\n")
    ini.append(r'nozzle_size = 0.4'+"\n")
    ini.append(r'print_speed = 40'+"\n")
    ini.append(r'print_temperature = 200'+"\n")
    ini.append(r'print_temperature2 = 0'+"\n")
    ini.append(r'print_temperature3 = 0'+"\n")
    ini.append(r'print_temperature4 = 0'+"\n")
    ini.append(r'print_temperature5 = 0'+"\n")
    ini.append(r'print_bed_temperature = 50'+"\n")
    ini.append(r'support = None'+"\n")
    ini.append(r'platform_adhesion = None'+"\n")
    ini.append(r'support_dual_extrusion = Both'+"\n")
    ini.append(r'wipe_tower = False'+"\n")
    ini.append(r'wipe_tower_volume = 50'+"\n")
    ini.append(r'ooze_shield = False'+"\n")
    ini.append(r'filament_diameter = 2.9'+"\n")
    ini.append(r'filament_diameter2 = 0'+"\n")
    ini.append(r'filament_diameter3 = 0'+"\n")
    ini.append(r'filament_diameter4 = 0'+"\n")
    ini.append(r'filament_diameter5 = 0'+"\n")
    ini.append(r'filament_flow = 100'+"\n")
    ini.append(r'retraction_speed = 40'+"\n")
    ini.append(r'retraction_amount = 4'+"\n")
    ini.append(r'retraction_dual_amount = 8'+"\n")
    ini.append(r'retraction_min_travel = 1.5'+"\n")
    ini.append(r'retraction_combing = All'+"\n")
    ini.append(r'retraction_minimal_extrusion = 0'+"\n")
    ini.append(r'retraction_hop = 0.05'+"\n")
    ini.append(r'bottom_thickness = 0.25'+"\n")
    ini.append(r'layer0_width_factor = 100'+"\n")
    ini.append(r'object_sink = 0'+"\n")
    ini.append(r'overlap_dual = 0.15'+"\n")
    ini.append(r'travel_speed = 200'+"\n")
    ini.append(r'bottom_layer_speed = 40'+"\n")
    ini.append(r'infill_speed = 60'+"\n")
    ini.append(r'solidarea_speed = 40'+"\n")
    ini.append(r'inset0_speed = 35'+"\n")
    ini.append(r'insetx_speed = 50'+"\n")
    ini.append(r'cool_min_layer_time = 5'+"\n")
    ini.append(r'fan_enabled = True'+"\n")
    ini.append(r'skirt_line_count = 2'+"\n")
    ini.append(r'skirt_gap = 2'+"\n")
    ini.append(r'skirt_minimal_length = 150.0'+"\n")
    ini.append(r'fan_full_height = 0.5'+"\n")
    ini.append(r'fan_speed = 100'+"\n")
    ini.append(r'fan_speed_max = 100'+"\n")
    ini.append(r'cool_min_feedrate = 10'+"\n")
    ini.append(r'cool_head_lift = False'+"\n")
    ini.append(r'solid_top = True'+"\n")
    ini.append(r'solid_bottom = True'+"\n")
    ini.append(r'fill_overlap = 15'+"\n")
    ini.append(r'perimeter_before_infill = True'+"\n")
    ini.append(r'support_type = Lines'+"\n")
    ini.append(r'support_angle = 65'+"\n")
    ini.append(r'support_fill_rate = 40'+"\n")
    ini.append(r'support_xy_distance = 0.7'+"\n")
    ini.append(r'support_z_distance = 0.2'+"\n")
    ini.append(r'spiralize = False'+"\n")
    ini.append(r'simple_mode = False'+"\n")
    ini.append(r'brim_line_count = 5'+"\n")
    ini.append(r'raft_margin = 5.0'+"\n")
    ini.append(r'raft_line_spacing = 3.0'+"\n")
    ini.append(r'raft_base_thickness = 0.3'+"\n")
    ini.append(r'raft_base_linewidth = 1.0'+"\n")
    ini.append(r'raft_interface_thickness = 0.27'+"\n")
    ini.append(r'raft_interface_linewidth = 0.4'+"\n")
    ini.append(r'raft_airgap_all = 0.0'+"\n")
    ini.append(r'raft_airgap = 0.22'+"\n")
    ini.append(r'raft_surface_layers = 2'+"\n")
    ini.append(r'raft_surface_thickness = 0.27'+"\n")
    ini.append(r'raft_surface_linewidth = 0.4'+"\n")
    ini.append(r'fix_horrible_union_all_type_a = True'+"\n")
    ini.append(r'fix_horrible_union_all_type_b = False'+"\n")
    ini.append(r'fix_horrible_use_open_bits = False'+"\n")
    ini.append(r'fix_horrible_extensive_stitching = False'+"\n")
    ini.append(r'plugin_config = '+'(lp1'+"\n")
    ini.append(r'   .'+"\n")
    ini.append(r'object_center_x = -1'+"\n")
    ini.append(r'object_center_y = -1'+"\n")
    ini.append(r'quality_fast = False'+"\n")
    ini.append(r'quality_standard = False'+"\n")
    ini.append(r'quality_high = False'+"\n")
    ini.append(r'quality_strong = False'+"\n")
    ini.append(r'extruder_left = False'+"\n")
    ini.append(r'extruder_right = False'+"\n")
    ini.append(r'material_pla = False'+"\n")
    ini.append(r'material_abs = False'+"\n")
    ini.append(r'material_fila = False'+"\n")
    ini.append(r'quality_fast_dual = False'+"\n")
    ini.append(r'quality_standard_dual = False'+"\n")
    ini.append(r'quality_high_dual = False'+"\n")
    ini.append(r'quality_strong_dual = False'+"\n")
    ini.append(r'pla_left_dual = False'+"\n")
    ini.append(r'abs_left_dual = False'+"\n")
    ini.append(r'fila_left_dual = False'+"\n")
    ini.append(r'pla_right_dual = False'+"\n")
    ini.append(r'abs_right_dual = False'+"\n")
    ini.append(r'fila_right_dual = False'+"\n")
    ini.append(r'pva_right_dual = False'+"\n")
    ini.append(r'dual_support = False'+"\n")

    ini.append(r'[alterations]'+"\n")
    ini.append(r'start.gcode = ;Sliced at: {day} {date} {time}'+"\n")
    ini.append(r'   ;Basic settings: Layer height: {layer_height} Walls: {wall_thickness} Fill: {fill_density}'+"\n")
    ini.append(r'   ;Print time: {print_time}'+"\n")
    ini.append(r'   ;Filament used: {filament_amount}m {filament_weight}g'+"\n")
    ini.append(r'   ;Filament cost: {filament_cost}'+"\n")
    ini.append(r'   ;M190 S{print_bed_temperature} ;Uncomment to add your own bed temperature line'+"\n")
    ini.append(r'   ;M109 S{print_temperature} ;Uncomment to add your own temperature line'+"\n")
    ini.append(r'   G21             ;metric values'+"\n")
    ini.append(r'   G90             ;absolute positioning'+"\n")
    ini.append(r'   M82             ;set extruder to absolute mode'+"\n")
    ini.append(r'   M107            ;start with the fan off'+"\n")
    ini.append(r'   G28 X0 Y0       ;move X/Y to min endstops'+"\n")
    ini.append(r'   G28 Z0          ;move Z to min endstops'+"\n")
    ini.append(r'   G92 E0          ;zero the extruded length'+"\n")
    ini.append(r'   G1 Z5 F200      ;Safety Z axis movement'+"\n")
    ini.append(r'   G1 F50 E7       ;extrude 7mm of feed stock'+"\n")
    ini.append(r'   G92 E0          ;zero the extruded length again'+"\n")
    ini.append(r'   G1 F200 E-4     ;Retract before printing'+"\n")
    ini.append(r'   G1 F{travel_speed}'+"\n")
    ini.append(r'   M117 Printing...    ;Put printing message on LCD screen'+"\n")
    ini.append(r'end.gcode = M104 S0'+"\n")
    ini.append(r'   M140 S0             ;heated bed heater off (if you have it)'+"\n")
    ini.append(r'   G91             ;relative positioning'+"\n")
    ini.append(r'   G1 Y+10 F{travel_speed}     ;move Z up a bit and retract filament even more'+"\n")
    ini.append(r'   G28 X0 Y0       ;move X/Y to min endstops, so the head is out of the way'+"\n")
    ini.append(r'   M84                 ;steppers off'+"\n")
    ini.append(r'   G90             ;absolute positioning'+"\n")
    ini.append(r'   ;{profile_string}'+"\n")
    ini.append(r'start2.gcode = ;Sliced at: {day} {date} {time}'+"\n")
    ini.append(r'   ;Basic settings: Layer height: {layer_height} Walls: {wall_thickness} Fill: {fill_density}'+"\n")
    ini.append(r'   ;Print time: {print_time}'+"\n")
    ini.append(r'   ;Filament used: {filament_amount}m {filament_weight}g'+"\n")
    ini.append(r'   ;Filament cost: {filament_cost}'+"\n")
    ini.append(r'   ;M190 S{print_bed_temperature} ;Uncomment to add your own bed temperature line'+"\n")
    ini.append(r'   ;M104 S{print_temperature} ;Uncomment to add your own temperature line'+"\n")
    ini.append(r'   ;M109 T1 S{print_temperature2} ;Uncomment to add your own temperature line'+"\n")
    ini.append(r'   ;M109 T0 S{print_temperature} ;Uncomment to add your own temperature line'+"\n")
    ini.append(r'   G21         ;metric values'+"\n")
    ini.append(r'   G90         ;absolute positioning'+"\n")
    ini.append(r'   M107        ;start with the fan off'+"\n")
    ini.append(r'   G28 X0 Y0   ;move X/Y to min endstops'+"\n")
    ini.append(r'   G28 Z0      ;move Z to min endstops'+"\n")
    ini.append(r'   T1              ;Switch to the 2nd extruder'+"\n")
    ini.append(r'   G92 E0          ;zero the extruded length'+"\n")
    ini.append(r'   G1 F100 E7  ;extrude 7mm of feed stock'+"\n")
    ini.append(r'   G92 E0          ;zero the extruded length again'+"\n")
    ini.append(r'   G1 F200 E-{retraction_dual_amount}'+"\n")
    ini.append(r'   T0          ;Switch to the first extruder'+"\n")
    ini.append(r'   G92 E0          ;zero the extruded length'+"\n")
    ini.append(r'   G1 F200 E7  ;extrude 7mm of feed stock'+"\n")
    ini.append(r'   G92 E0          ;zero the extruded length again'+"\n")
    ini.append(r'   G1 Z5 F200  ;Safety Z axis movement'+"\n")
    ini.append(r'   G1 F{travel_speed}'+"\n")
    ini.append(r'   M117 Printing...    ;Put printing message on LCD screen'+"\n")
    ini.append(r'end2.gcode = M104 T0 S0'+"\n")
    ini.append(r'   M104 T1 S0      ;extruder heater off'+"\n")
    ini.append(r'   M140 S0         ;heated bed heater off (if you have it)'+"\n")
    ini.append(r'   G91         ;relative positioning'+"\n")
    ini.append(r'   G1 Y+10 F{travel_speed} ;move Z up a bit and retract filament even more'+"\n")
    ini.append(r'   G28 X0 Y0       ;move X/Y to min endstops, so the head is out of the way'+"\n")
    ini.append(r'   M84             ;steppers off'+"\n")
    ini.append(r'   G90         ;absolute positioning'+"\n")
    ini.append(r'   ;{profile_string}'+"\n")
    ini.append(r'support_start.gcode = '+"\n")
    ini.append(r'support_end.gcode = '+"\n")
    ini.append(r'cool_start.gcode = '+"\n")
    ini.append(r'cool_end.gcode = '+"\n")
    ini.append(r'replace.csv = '+"\n")
    ini.append(r'preswitchextruder.gcode = ;Switch between the current extruder and the next extruder, when printing with multiple extruders.'+"\n")
    ini.append(r'   ;This code is added before the T(n)'+"\n")
    ini.append(r'postswitchextruder.gcode = ;Switch between the current extruder and the next extruder, when printing with multiple extruders.'+"\n")
    ini.append(r'   ;This code is added after the T(n)'+"\n")
    ini.append(r'   G1 F500 E-0.5'+"\n")
    ini.append(r'   G1 F50 E0.5'+"\n")
    ini.append(r'   G92 E0'+"\n")
    ini.append(r'   G1 F3000 E-4.5'+"\n")
    ini.append(r'   G1 F{travel_speed}'+"\n")
    if createFile == 'createFile':
        f = open(fileName+".ini", "w")
        f.writelines(ini)
        f.close()
    if createFile == 'noFile':
        print string.join(ini)
    if createFile == 'onlyFilename':
        print fileName+'.fff'
    return fileName+'.ini'

def getBundleSize():
    if ".BCN3D Sigma - Simplify3D Profiles temp" in os.listdir('.'):
        shutil.rmtree(".BCN3D Sigma - Simplify3D Profiles temp")
    os.mkdir(".BCN3D Sigma - Simplify3D Profiles temp")
    os.chdir(".BCN3D Sigma - Simplify3D Profiles temp")
    
    totalSmaProfiles = (len(profilesData['hotend'])-1) *  len(profilesData['filament']) * 2
    totalBigProfiles = (len(profilesData['hotend'])-1)**2 * len(profilesData['filament'])**2

    fileNameBig = createSimplify3DProfile(profilesData['hotend'][0], profilesData['hotend'][0], profilesData['filament'][0], profilesData['filament'][0], 'noData', 'createFile')
    fileNameSmall = createSimplify3DProfile(profilesData['hotend'][0], profilesData['hotend'][-1], profilesData['filament'][0], profilesData['filament'][0], 'noData', 'createFile')
    
    oneLineCsvSize = float(10494984)/78480 # experimental value
    csvSize = oneLineCsvSize * (totalSmaProfiles*len(profilesData['quality']) + totalBigProfiles*len(profilesData['quality'])*3)
    bundleSize = totalSmaProfiles*os.path.getsize(fileNameSmall)+totalBigProfiles*os.path.getsize(fileNameBig) + csvSize

    os.chdir('..')
    shutil.rmtree(".BCN3D Sigma - Simplify3D Profiles temp")
    return bundleSize*1.05

def createProfilesBundle(dataLog, profilesCreatedCount):    
    y = 'y'
    if getBundleSize()/1024/1024 >= 150: # define Size limit to notice (in MB)
        print ' Estimated space needed during the process: '+str(int(getBundleSize()*1.075/1024/1024))+' MB.'
        print ' Estimated final bundle size: '+str(int(getBundleSize()*0.075/1024/1024))+' MB.'
        print ' Do you want to continue? (Y/n)'
        while y not in ['Y', 'n']:
            y = raw_input(' ')
        print
    else:
        y = 'Y'
    if y == 'Y':
        totalSmaProfiles = (len(profilesData['hotend'])-1) *  len(profilesData['filament']) * 2
        totalBigProfiles = (len(profilesData['hotend'])-1)**2 * len(profilesData['filament'])**2
        totalProfilesAvailable = totalSmaProfiles + totalBigProfiles
        if ".BCN3D Sigma - Simplify3D Profiles temp" in os.listdir('.'):
            shutil.rmtree(".BCN3D Sigma - Simplify3D Profiles temp")
        os.mkdir(".BCN3D Sigma - Simplify3D Profiles temp")
        os.chdir(".BCN3D Sigma - Simplify3D Profiles temp")
        for hotendLeft in sorted(profilesData['hotend'], key=lambda k: k['id']):
            if hotendLeft['id'] != 'None':
                os.mkdir("Left Hotend "+hotendLeft['id'])
                os.chdir("Left Hotend "+hotendLeft['id'])
            else:
                os.mkdir("No Left Hotend")
                os.chdir("No Left Hotend")
            for hotendRight in sorted(profilesData['hotend'], key=lambda k: k['id']):
                if hotendRight['id'] != 'None':
                    os.mkdir("Right Hotend "+hotendRight['id'])
                    os.chdir("Right Hotend "+hotendRight['id'])
                else:                
                    os.mkdir("No Right Hotend")
                    os.chdir("No Right Hotend")
                for filamentLeft in sorted(profilesData['filament'], key=lambda k: k['id']):
                    for filamentRight in sorted(profilesData['filament'], key=lambda k: k['id']):
                        if hotendRight['id'] == 'None' and hotendLeft['id'] == 'None':
                            break
                        profilesCreatedCount += 1
                        createSimplify3DProfile(hotendLeft, hotendRight, filamentLeft, filamentRight, dataLog, 'createFile')
                        sys.stdout.write("\r Progress: %d%%" % int(float(profilesCreatedCount)/totalProfilesAvailable*100))
                        sys.stdout.flush()
                        if hotendRight['id'] == 'None':
                            break
                    if hotendLeft['id'] == 'None':
                        break
                os.chdir('..')
            os.chdir('..')
        csv = open("BCN3D Sigma - Simplify3D Profiles.csv", "w")
        csv.writelines(dataLog)
        csv.close()
        os.chdir('..')
        sys.stdout.write("\r Progress: Creating the zip file...")
        sys.stdout.flush()
        shutil.make_archive('BCN3D Sigma - Simplify3D Profiles', 'zip', '.BCN3D Sigma - Simplify3D Profiles temp')
        shutil.rmtree(".BCN3D Sigma - Simplify3D Profiles temp")
        print("\r Your bundle 'BCN3D Sigma - Simplify3D Profiles.zip' is ready. Enjoy!\n")
        return profilesCreatedCount
    else:
        return 0

def testAllCombinations():
    combinationCount = 0
    totalProfilesAvailable = len(profilesData['hotend'])**2 * len(profilesData['filament'])**2
    for hotendLeft in sorted(profilesData['hotend'], key=lambda k: k['id']):
        for hotendRight in sorted(profilesData['hotend'], key=lambda k: k['id']):
            for filamentLeft in sorted(profilesData['filament'], key=lambda k: k['id']):
                for filamentRight in sorted(profilesData['filament'], key=lambda k: k['id']):
                    createSimplify3DProfile(hotendLeft, hotendRight, filamentLeft, filamentRight, 'noData', 'nothing')
                    combinationCount += 1
                    sys.stdout.write("\r Progress: %d%%" % int(float(combinationCount)/totalProfilesAvailable*100))
                    sys.stdout.flush()
    print '\r All '+str(combinationCount)+' profiles can be generated!\n'

def selectHotendAndFilament(extruder):
    print "\n Select Sigma's "+extruder+" Hotend (1-"+str(len(profilesData['hotend']))+'):'
    answer0 = ''
    hotendOptions = []
    for c in range(len(profilesData['hotend'])):
        hotendOptions.append(str(c+1))
    hotendOptions.append(str(c+2))
    materialOptions = []
    for c in range(len(profilesData['filament'])):
        materialOptions.append(str(c+1))
    for hotend in range(len(profilesData['hotend'])):
        print ' '+str(hotend+1)+'. '+sorted(profilesData['hotend'], key=lambda k: k['id'])[hotend]['id']
    while answer0 not in hotendOptions:
        answer0 = raw_input(' ')
    print ' '+extruder+' Hotend: '+sorted(profilesData['hotend'], key=lambda k: k['id'])[int(answer0)-1]['id']
    if answer0 != str(int(hotendOptions[-1])-1):
        print "\n Select Sigma's "+extruder+" Extruder Loaded Filament (1-"+str(len(profilesData['filament']))+'):'
        answer1 = ''
        for material in range(len(profilesData['filament'])):
            print ' '+str(material+1)+'. '+sorted(profilesData['filament'], key=lambda k: k['id'])[material]['id']
        while answer1 not in materialOptions:
            answer1 = raw_input(' ')
        print ' '+extruder+' Extruder Filament: '+sorted(profilesData['filament'], key=lambda k: k['id'])[int(answer1)-1]['id']+'.'
    else:
        answer1 = '1'
    return (int(answer0)-1, int(answer1)-1)

def validArguments():
    if len(sys.argv) == 6 or len(sys.argv) == 7:
        leftHotend = sys.argv[1]+'.json' in os.listdir('./Profiles Data/Hotends') or sys.argv[1] == 'None'
        rightHontend = sys.argv[2]+'.json' in os.listdir('./Profiles Data/Hotends') or sys.argv[2] == 'None'
        leftFilament = sys.argv[3]+'.json' in os.listdir('./Profiles Data/Filaments') or (sys.argv[1] == 'None' and sys.argv[3] == 'None')
        rightFilament = sys.argv[4]+'.json' in os.listdir('./Profiles Data/Filaments') or (sys.argv[2] == 'None' and sys.argv[4] == 'None')
        software = sys.argv[5] == '--cura' or sys.argv[5] == '--simplify3d'
        if len(sys.argv) == 7:
            fileAction = sys.argv[6] == '--no-file' or sys.argv[6] == '--only-filename'
            return leftHotend and rightHontend and leftFilament and rightFilament and software and fileAction
        else:
            return leftHotend and rightHontend and leftFilament and rightFilament and software
    else:
        return False

def readProfilesData():
    global profilesData
    profilesData = dict([("hotend", []), ("filament", []), ("quality", [])])
    for hotend in os.listdir('./Profiles Data/Hotends'):
        if hotend[-5:] == '.json':
            with open('./Profiles Data/Hotends/'+hotend) as hotend_file:    
                hotendData = json.load(hotend_file)
                profilesData['hotend'].append(hotendData)
    profilesData['hotend'].append(dict([('id', 'None')]))
    for filament in os.listdir('./Profiles Data/Filaments'):
        if filament[-5:] == '.json':
            with open('./Profiles Data/Filaments/'+filament) as filament_file:    
                filamentData = json.load(filament_file)
                profilesData['filament'].append(filamentData)
    for quality in os.listdir('./Profiles Data/Quality Presets'):
        if quality[-5:] == '.json':
            with open('./Profiles Data/Quality Presets/'+quality) as quality_file:    
                qualityData = json.load(quality_file)
                profilesData['quality'].append(qualityData)

def main():
    if validArguments():
        readProfilesData()
        for hotend in os.listdir('./Profiles Data/Hotends'):
            if hotend == sys.argv[1]+'.json':
                with open('./Profiles Data/Hotends/'+hotend) as hotend_file:    
                    leftHotend = json.load(hotend_file)
            if hotend == sys.argv[2]+'.json':
                with open('./Profiles Data/Hotends/'+hotend) as hotend_file:    
                    rightHotend = json.load(hotend_file)
        for filament in os.listdir('./Profiles Data/Filaments'):
            if filament == sys.argv[3]+'.json':
                with open('./Profiles Data/Filaments/'+filament) as filament_file:    
                    leftFilament = json.load(filament_file)
            if filament == sys.argv[4]+'.json':
                with open('./Profiles Data/Filaments/'+filament) as filament_file:    
                    rightFilament = json.load(filament_file)
        if sys.argv[3] == 'None':
            leftFilament = profilesData['filament'][0]
        if sys.argv[4] == 'None':
            rightFilament = profilesData['filament'][0]
        if len(sys.argv) == 7:
            if sys.argv[6] == '--no-file':
                createSimplify3DProfile(leftHotend, rightHotend, leftFilament, rightFilament, 'noData', 'noFile')
            if sys.argv[6] == '--only-filename':
                createSimplify3DProfile(leftHotend, rightHotend, leftFilament, rightFilament, 'noData', 'onlyFilename')
        else:
            createSimplify3DProfile(leftHotend, rightHotend, leftFilament, rightFilament, 'noData', 'createFile')
    else:
        if len(sys.argv) == 1:
            print '\n Welcome to the BCN3D Sigma Profile Generator for Simplify3D \n'
            while True:
                print ' Choose one option (1-4):'
                print ' 1. Generate a bundle of profiles'
                print ' 2. Generate one single profile'
                print ' 3. Test all combinations'
                print ' 4. Exit'
                x = 'x'
                y = 'y'
                while x not in '1234':
                    x = raw_input(' ')
                dataLog = ["LFilament;RFilament;Extruder;Quality;LNozzle;RNozzle;InfillExt;PrimaryExt;SupportExt;LFlow;RFlow;Layers/Infill;DefaultSpeed;FirstLayerUnderspeed;OutLineUnderspeed;SupportUnderspeed;FirstLayerHeightPercentage;LTemp;RTemp;BTemp;\n"]
                profilesCreatedCount = 0
                readProfilesData()
                if x in '12':
                    if x == '1':
                        profilesCreatedCount = createProfilesBundle(dataLog, profilesCreatedCount)
                        if profilesCreatedCount > 0:
                            print ' See profile(s) data? (Y/n)'
                            while y not in ['Y', 'n']:
                                y = raw_input(' ')
                    elif x == '2':
                        a = selectHotendAndFilament('Left')
                        b = selectHotendAndFilament('Right')
                        if sorted(profilesData['hotend'], key=lambda k: k['id'])[a[0]]['id'] == 'None' and sorted(profilesData['hotend'], key=lambda k: k['id'])[b[0]]['id'] == 'None':
                            print "\n Select at least one hotend to create a profile.\n"
                        else:
                            print "\n Your new profile '"+createSimplify3DProfile(sorted(profilesData['hotend'], key=lambda k: k['id'])[a[0]], sorted(profilesData['hotend'], key=lambda k: k['id'])[b[0]], sorted(profilesData['filament'], key=lambda k: k['id'])[a[1]], sorted(profilesData['filament'], key=lambda k: k['id'])[b[1]], dataLog, 'createFile')+"' has been created.\n"
                            profilesCreatedCount = 1
                            print ' See profile(s) data? (Y/n)'
                            while y not in ['Y', 'n']:
                                y = raw_input(' ')
                    if y == 'Y':
                        for l in dataLog:
                            print '',
                            for d in string.split(l, ';'):
                                print string.rjust(str(d)[:6], 6),
                        print ' '+str(profilesCreatedCount)+' profile(s) created with '+str(len(dataLog)-1)+' configurations.\n'
                elif x == '3':
                    testAllCombinations()
                elif x == '4':
                    print '\n Until next time!\n'
                    break

if __name__ == '__main__':
    main() 