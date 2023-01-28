import os
import uuid
import csv
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("directory",help="path to directory containing csv files")
parser.add_argument("-s","--safe",action="store_true",help="overwrite files even if they have UUIDs already")
args = parser.parse_args()

indir = args.directory
outdir = indir
if args.safe:
    outdir = os.path.join(indir,"csvswithuuids")
    
if not os.path.isdir(outdir):
    os.makedirs(outdir)

def addUUIDColumn(csv_file,outdir,header_row=False):

    filename = os.path.basename(csv_file)
    outfile = os.path.join(outdir,filename)

    print filename

    outrows = []
    with open(csv_file,'rb') as csvopen:
        reader = csv.reader(csvopen)
        if header_row:
            headers = reader.next()
            if headers[-1] == "UUID":
                print "  UUIDs already present in this file"
                return
            headers.append("UUID")
            outrows.append(headers)
            
        for row in reader:
            try:
                uuid.UUID(row[-1])
                print "  UUIDs already present in this file"
                return
            except:
                row.append(str(uuid.uuid4()))
            outrows.append(row)
    
    with open(outfile,'wb') as csvout:
        writer = csv.writer(csvout)
        for row in outrows:
            writer.writerow(row)

    print "  done"



for f in [i for i in os.listdir(indir) if i.endswith(".csv")]:
    addUUIDColumn(os.path.join(indir,f),outdir)


    
