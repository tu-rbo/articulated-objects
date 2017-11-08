#!/usr/bin/python

"""
Created on Wed Oct 11 17:52:55 2017

@author: Roberto Martin-Martin
"""

import os
import sys
import json
import urllib
import urllib2
import argparse
import errno 
import csv
import ntpath

dataset_url = "https://zenodo.org/record/1036660/files/"
interactions_index_url = dataset_url + "interactions_index.csv"
    
def mkdir_p(path):
    """Generate a folder recursively (like mkdir -p).

    Argument:
    path -- string with the full path and name of the folder to generate
    """
    try:
        os.makedirs(path)
    except OSError as exc:  # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise

def download_file(url, filename):
    u = urllib2.urlopen(url)
    mkdir_p(ntpath.dirname(filename))
    f = open(filename, 'wb')
    meta = u.info()
    file_size = int(meta.getheaders("Content-Length")[0])
    print "Downloading: %s (%s MB)" % (filename, file_size/1000000.0)

    file_size_dl = 0
    block_sz = 65536
    while True:
        buffer = u.read(block_sz)
        if not buffer:
            break

        file_size_dl += len(buffer)
        f.write(buffer)
        status = r"%10d  [%3.2f%%]" % (file_size_dl/1000000.0, file_size_dl * 100. / file_size)
        status = status + chr(8)*(len(status)+1)
        print status,
    f.close()

def extract_tgz(filename, dir):
    mkdir_p(ntpath.dirname(filename))
    tar_command = "tar -xzf {filename} -C {dir}".format(filename=filename,dir=dir)
    os.system(tar_command)
    os.remove(filename)

def check_url(url):
    try:
        request = urllib2.Request(url)
        request.get_method = lambda : 'HEAD'
        response = urllib2.urlopen(request)
        return True
    except Exception as e:
        return False
            
all_objects = ['globe',
               'laptop',
               'ikea',
               'foldingrule',
               'book',
               'treasurebox',
               'tripod',
               'clamp',
               'pliers',
               'cardboardbox',
               'rubikscube',
               'microwave',
               'ikeasmall',
               'cabinet']
               
backgrounds = ['plain','textured','black']
lightings = ['artificial','dark','natural']
internal_dofs = ['only_internal_dofs','int_and_ext_dofs']  
camera_motions = ['no_cam_motion','with_cam_motion']  
clutters = ['no_clutter','with_clutter']    
ft_meas = ['no_ft','with_ft'] 

def deparse_property(prop):
    if prop.startswith('no_') or prop.startswith('int_'):
        return '0'
    elif prop.startswith('with_') or prop.startswith('only_'):
        return '1'
    else:
        return prop

if __name__ == "__main__":
    
    parser = argparse.ArgumentParser(description='Script to download and decompress data from the RBO dataset of articulated objects and interactions.', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--no_decomp', action='store_true', default = False,
                        help='Do not decompress automatically the downloaded data.')
    parser.add_argument('--output_dir', type=str, default = '.',
                        help='Root directory to download and generate the dataset')
    parser.add_argument('--objects', nargs='*', default = 'all',
                        help='Object models to download. Pass \"--objects none\" to skip.')
    parser.add_argument('--interactions', nargs='*', default = 'all',
                        help='Interactions to download. You can specify individual interactions (<objectName><InteractionIndex>) or groups of interactions by object (<objectName>) or by interaction property, e.g. \"dark\" or \"with_ft\" (see groups with --groups). Pass \"--interactions none\" to skip.')
    parser.add_argument('--groups', action='store_true', default = False,
                        help='Print the groups of interactions available.')
    parser.add_argument('--ros', action='store_true', default = False,
                        help='Download ROS bags instead of raw sensor data.')
    args = parser.parse_args()
    
    #Print the groups of interactions available
    if args.groups:
        print "\tType of backgrounds: " + str(backgrounds)    
        print "\tType of lighting: " + str(lightings)
        print "\tType of actuation: " + str(internal_dofs)
        print "\tCamera motion: " + str(camera_motions)
        print "\tClutter: " + str(clutters)
        print "\tForce-torque measurements: " + str(ft_meas)
        exit()
        
    if args.ros: print "Downloading ROS bags instead of raw sensor data"
    
    #Create the directory structure
    print "Directory structure for the dataset at: " + args.output_dir + '/rbo_dataset'
    mkdir_p(args.output_dir + '/rbo_dataset')
    mkdir_p(args.output_dir + '/rbo_dataset/objects')
    mkdir_p(args.output_dir + '/rbo_dataset/interactions')
    
    if args.objects == 'all': args.objects = all_objects
    
    if args.objects != ['none']:
        #Download the model files of the given objects
        for name in args.objects:
            if name not in all_objects:
                print "Wrong object name passed: " + name    
            elif not check_url(dataset_url + name + '.tar.gz'):
                print "Connection error! Cannot download model of " + name
            else:
                model_file = name + '.tar.gz'
                download_file(dataset_url + model_file, args.output_dir + '/rbo_dataset/objects/' + model_file)
                if not args.no_decomp:
                    extract_tgz(args.output_dir + '/rbo_dataset/objects/' +model_file, args.output_dir + '/rbo_dataset/objects/')
            
    #Download the .csv with the information of the interactions
    ii_filename = args.output_dir + '/rbo_dataset/interactions/interactions_index.csv'
    if not os.path.isfile(ii_filename):
        print "Downloading dataset index"
        if not check_url(interactions_index_url):
            print "Connection error!"
        else:
            download_file(interactions_index_url, ii_filename)
            
    #Generate a list with all the interactions
    ii = csv.reader(open(ii_filename))
    all_interactions = []
    for i in ii:
        all_interactions += [i[0]]
        
    props_dict = {}
    props_dict[2] = backgrounds
    props_dict[3] = lightings
    props_dict[4] = camera_motions
    props_dict[5] = internal_dofs
    props_dict[7] = clutters
    props_dict[8] = ft_meas
    
    #Download the interaction files requested
    if args.interactions != 'none':
        for inter in args.interactions:
            #inter is an object name
            if inter in all_objects:
                print "Download all the interactions with " + inter
                ii = csv.reader(open(ii_filename))
                for i in ii:
                    if i[1] == inter:
                        interaction_file =  i[0] + ['_o.tar.gz','.bag'][args.ros]
                        interaction_obj_folder = args.output_dir + '/rbo_dataset/interactions/' + i[1] + '/'
                        interaction_subfolder = interaction_obj_folder + i[0] + '/'
                        if not check_url(dataset_url + interaction_file):
                            print "Connection error! Cannot download interaction " + interaction_file + " from url: " + dataset_url + interaction_file
                        else:                        
                            download_file(dataset_url + interaction_file, interaction_obj_folder + interaction_file)
                            if not args.no_decomp and not args.ros:
                                print "Extracting"
                                extract_tgz(interaction_obj_folder + interaction_file, interaction_obj_folder)
            #inter is a specific interaction
            elif inter in all_interactions:
                print "Download the interaction " + inter
                object_name_int = inter[0:-2]
                interaction_file = inter + ['_o.tar.gz','.bag'][args.ros]     
                interaction_obj_folder = args.output_dir + '/rbo_dataset/interactions/' + object_name_int + '/'
                interaction_subfolder = interaction_obj_folder + inter  + '/'
                if not check_url(dataset_url + interaction_file):
                    print "Connection error! Cannot download interaction " + interaction_file + " from url: " + dataset_url + interaction_file
                else:                        
                    download_file(dataset_url + interaction_file, interaction_obj_folder + interaction_file)
                    if not args.no_decomp and not args.ros:
                        print "Extracting"
                        extract_tgz(interaction_obj_folder + interaction_file, interaction_obj_folder)
            else:
                for prop_id in props_dict:
                    if inter in props_dict[prop_id]:
                        print "Download the interactions by property: "  + inter
                        ii = csv.reader(open(ii_filename))
                        for i in ii:
                            if i[prop_id] == deparse_property(inter):
                                interaction_file =  i[0] + ['_o.tar.gz','.bag'][args.ros]
                                interaction_obj_folder = args.output_dir + '/rbo_dataset/interactions/' + i[1] + '/'
                                interaction_subfolder = interaction_obj_folder  + i[0] + '/'
                                if not check_url(dataset_url + interaction_file):
                                    print "Connection error! Cannot download interaction " + interaction_file + " from url: " + dataset_url + interaction_file
                                else:                        
                                    download_file(dataset_url + interaction_file, interaction_obj_folder + interaction_file)
                                    if not args.no_decomp and not args.ros:
                                        print "Extracting"
                                        extract_tgz(interaction_obj_folder + interaction_file, interaction_obj_folder)
