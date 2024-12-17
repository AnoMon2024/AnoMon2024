# AnoMon: Network-wide Measurement on Anomalies

This repository contains all related code of our paper "AnoMon: Network-wide Measurement on Anomalies". 

## Introduction

Network measurement is crucial for successful network maintenance. The contradiction between limited measurement resources and immense network traffic has always been a great challenge for network measurement. An ideal measurement system should achieve reduced monitoring overhead that does not grow with the traffic scale. Towards this goal, this paper presents AnoMon, an efficient and accurate network measurement system. Our design philosophy is to first identify the flow groups that contains abnormal traffic, which are named abnormal flow groups (AFG), with coarse-grained passive measurement at network edge, and then monitor the traffic in AFG with fine-grained active measurement inside the network. We fully implement an AnoMon prototype in a testbed built with programmable switches and conduct extensive experiments. Experimental results show that AnoMon achieves up to 4.0¡Á and 5.6¡Á higher accuracy in locating anomalies compared to alwayson LightGuardian and Marple; and AnoMon achieves up to 3.9¡Á smaller bandwidth overhead compared to trigger-based NetSeer. All codes are released anonymously1.

## About this repository

* `CPU` contains codes of AnoSketch and AnoTable implemented on CPU platforms. 
* `NSPY` contains codes implemneted on NS.PY simulation platform. 
* `testbed` contains codes related to our testbed. We have deployed AnoMon in a testbed built with 10 Edgecore
Wedge 100BF-32X switches (with Tofino ASICs) and 8 endhosts in the FatTree topology.
* More details can be found in the folders.