# -*- coding: utf-8 -*-
# Colm Coughlan 16.3.2015
# Merge two bbs files, assuming second is contained entirely within the radius of the first and should be used preferentially after clipping
# N.B. Clipping could be a very good idea for thermal sources in the second dataset if the imaging freq is far from its ref. frequency as PyBDSM assumes a spectral index of -0.8

import sys
import numpy as np
from pylab import plot,show

min_length = 3	# ignore entry lines shorter than this
min_size = 1e-10	# SAGECal chunk size (hybrid solution intervals only)


# function to convert RA and DEC strings into degree floats

def gen_coords(data, ra_col, dec_col):
	coords = np.zeros((len(data),2),dtype=float)
	for i in range(len(data)):
		ra = data[i,ra_col].split(':')
		coords[i,0] = float(ra[0])*15 + float(ra[1])*0.25 + float(ra[2])/240.0
		dec = data[i,dec_col].split('.',3)
		coords[i,1] = float(dec[0]) + float(dec[1])/60.0 + float(dec[2])/360.
	return(coords)z

	

# Check arguments

if(len(sys.argv)!=8):
	print("\tError: Takes 7 arguments.")
	print("\tUseage: gen_cluster <filename1> <filename2> <centre> <radius> <clip filename 2 at (Jy)> <outputname> <type>")
	print('\tCentre should be in the form 04:21:59.408_+19.32.07.147')
	print('\tRadius is assumed to be in mas')
	print('\tType = 0 for bbs, 1 for SAGEcal local sky model')
	sys.exit()
else:
	inputname1 = str(sys.argv[1])
	inputname2 = str(sys.argv[2])
	centre = str(sys.argv[3])
	ra = centre.split("_")[0].split(':')
	dec = centre.split("_")[1].split('.',3)
	centre_coords = [ float(ra[0])*15 + float(ra[1])*0.25 + float(ra[2])/240.0 , float(dec[0]) + float(dec[1])/60.0 + float(dec[2])/360.]
	radius = float(sys.argv[4])/3600.
	clip = float(sys.argv[5])
	outputname = str(sys.argv[6])
	outputtype = int(sys.argv[7])
	print("\tReading: "+inputname1+", "+inputname2)
	print("\tWriting: "+outputname)


# Attempt to open input file 1

try:
	f = open(inputname1)
except:
	print("\tError opening "+inputname1)
	sys.exit()


# Read format string and get rid of any blank lines or comments

ctr = 0
nodata=True
while(nodata):
	line = f.readline()
	# Check for blank lines or comments
	if( len(line)<min_length or line[0]=='#' ):
		ctr = ctr + 1
	else:
		# read format string
		if( line.split(" ")[0]=='format' ):
			saved_format = line
			formatstr = line.split(" = ")[1].split(", ")
			print("\tDetected format = "+str(formatstr))
			for i in range(len(formatstr)):
				if formatstr[i]=='Name':
					name_col = i
				if formatstr[i]=='Type':
					type_col = i
				if formatstr[i]=='Ra':
					ra_col = i
				if formatstr[i]=='Dec':
					dec_col = i
				if formatstr[i]=='I':
					flux_col = i
				if formatstr[i]=='Q':
					q_col = i
				if formatstr[i]=='U':
					u_col = i
				if formatstr[i]=='V':
					v_col = i
				if formatstr[i]=='MajorAxis':
					major_axis_col = i
				if formatstr[i]=='MinorAxis':
					minor_axis_col = i
				if formatstr[i]=='Orientation':
					bpa_col = i
				if formatstr[i].split("=")[0]=='ReferenceFrequency':
#					ref_freq = float(formatstr[i].split("\'")[1])	# Don't use this - it might be different between skymodels (read on per source basis)
					ref_freq_col = i
				if formatstr[i].split("=")[0]=='SpectralIndex':
					spectral_col = i
			ctr = ctr + 1
		else:
			# presume we have reached the data
			nodata=False
			f.close()

# Read in data as strings
data1 = np.genfromtxt(inputname1,delimiter=', ',dtype=str,skip_header = ctr-1)
data2 = np.genfromtxt(inputname2,delimiter=', ',dtype=str,skip_header = ctr-1)

# Convert to coords in degrees
coords1 = gen_coords(data1,ra_col,dec_col)

# Write out as BBS
nclip = 0
if outputtype==0:

	try:
		f = open(outputname,'w')
	except:
		print "\tError opening ", outputname
		sys.exit()

	f.write(saved_format)
	f.write('\n')

	for i in range(len(data2)):
		if(float(data2[i][flux_col])>clip):
			f.write(data2[i][0])
			for j in range(1,len(data2[i])):
				f.write(', '+data2[i][j])
			f.write('\n')
		else:
			nclip = nclip + 1

	x = np.subtract(coords1, centre_coords)	# find radius of each point in first dataset
	rad_lst = np.sum(np.abs(x)**2,axis=-1)**(1./2)

	kept = 0
	for i in range(len(data1)):
		if rad_lst[i] > radius:
			kept = kept + 1
			f.write(data1[i][0])
			for j in range(1,len(data1[i])):
				f.write(', '+data1[i][j])
			f.write('\n')

	f.close
	print('\tMerger complete.')
	print('\t\t'+str(nclip)+' sources out of '+str(len(data2))+' clipped from '+inputname2)
	print('\t\t'+str(len(data1) - kept)+' sources out of '+str(len(data1))+' excluded from '+inputname1)
	print('\t\t'+str(len(data2) + kept - nclip)+' sources in '+outputname)
	print('\t\tWarning: No check for bad Gaussians performed. If using SAGECal use this mode for gencluster2 input, but mode=1 for SAGECal input.')

# Write out as LSM

else:
	nbad = 0
	nclip = 0
	try:
		f = open(outputname,'w')
	except:
		print "\tError opening ", outputname
		sys.exit()

	f.write('# SAGECal sky model\n')
	f.write('# Generated by merge_bbs.py. IMPORTANT: A value of zero has been assumed for all RM values. merge_bbs.py does not import them.\n')
	f.write('# Name  | RA (hr,min,sec) | DEC (deg,min,sec) | I | Q | U | V | SI | RM | eX | eY | eP | freq0\n')
	f.write('\n')

	for i in range(len(data2)):
		if(float(data2[i][flux_col])>clip):
			if(data2[i][type_col] == 'GAUSSIAN'):
				f.write('G'+data2[i][0])
			else:
				f.write('P'+data2[i][0])
			f.write(' '+data2[i][ra_col].replace(":"," "))
			f.write(' '+data2[i][dec_col].replace("."," ",2))
			f.write(' '+data2[i][flux_col])
			f.write(' '+data2[i][q_col])
			f.write(' '+data2[i][u_col])
			f.write(' '+data2[i][v_col])
			f.write(' '+data2[i][spectral_col].strip('[]'))
			f.write(' 0') # Assuming zero RM
			f.write(' '+str(float(data2[i][major_axis_col])*(np.pi/180.0)/(2*3600.0)))
			if ((float(data2[i][minor_axis_col]) > min_size and data2[i][type_col] == 'GAUSSIAN') or data2[i][type_col] == 'POINT'):
				f.write(' '+str(float(data2[i][minor_axis_col])*(np.pi/180.0)/(2*3600.0))) # Watch out for unusually low bmin - > Bug in PyBDSM write_catalog? The corresponding fits look fine in the viewer
			else:
				f.write(' '+str(float(data2[i][major_axis_col])*(np.pi/180.0)/(2*3600.0)))
				nbad = nbad + 1
			f.write(' '+str((float(data2[i][bpa_col])-90.0)*(np.pi/180.0)))
			f.write(' '+data2[i][ref_freq_col])
			f.write('\n')
		else:
			nclip = nclip + 1

	x = np.subtract(coords1, centre_coords)	# find radius of each point in first dataset
	rad_lst = np.sum(np.abs(x)**2,axis=-1)**(1./2)

	kept = 0
	for i in range(len(data1)):
		if rad_lst[i] > radius:
			kept = kept + 1
			if(data1[i][type_col] == 'GAUSSIAN'):
				f.write('G'+data1[i][0])
			else:
				f.write('P'+data1[i][0])
			f.write(' '+data1[i][ra_col].replace(":"," "))
			f.write(' '+data1[i][dec_col].replace("."," ",2))
			f.write(' '+data1[i][flux_col])
			f.write(' '+data1[i][q_col])
			f.write(' '+data1[i][u_col])
			f.write(' '+data1[i][v_col])
			f.write(' '+data1[i][spectral_col].strip('[]'))
			f.write(' 0') # Assuming zero RM
			f.write(' '+str(float(data1[i][major_axis_col])*(np.pi/180.0)/(2*3600.0)))
			if ((float(data1[i][minor_axis_col]) > min_size and data1[i][type_col] == 'GAUSSIAN') or data1[i][type_col] == 'POINT'):
				f.write(' '+str(float(data1[i][minor_axis_col])*(np.pi/180.0)/(2*3600.0))) # Watch out for unusually low bmin - > Bug in PyBDSM write_catalog? The corresponding fits look fine in the viewer
			else:
				f.write(' '+str(float(data1[i][major_axis_col])*(np.pi/180.0)/(2*3600.0)))
				nbad = nbad + 1
			f.write(' '+str((float(data1[i][bpa_col])-90.0)*(np.pi/180.0)))
			f.write(' '+data1[i][ref_freq_col])
			f.write('\n')

	f.close
	print('\tMerger complete.')
	print('\t\t'+str(nclip)+' sources out of '+str(len(data2))+' clipped from '+inputname2)
	print('\t\t'+str(len(data1) - kept)+' sources out of '+str(len(data1))+' excluded from '+inputname1)
	print('\t\t'+str(len(data2) + kept - nclip)+' sources in '+outputname)
	print('\t\tA total of '+str(nbad)+' bad Gaussians detected and assumed to be circular')
	f.close
