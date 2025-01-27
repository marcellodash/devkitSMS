#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Author: sverx
# Version: 2.7.1 (bugfix)

from __future__ import absolute_import, division, generators, unicode_literals, print_function, nested_scopes
import sys
import os.path
import array


class Modify:
    def __init__(self, operator, start, length, values):
        self.operator = operator
        self.start = start
        self.length = length
        self.values = values

class Asset:
    def __init__(self, name, size):
        self.name = name
        self.o_size = size
        self.size = size
        self.style = 0
        self.modifies = []
        self.header = []
        self.footer = []
        self.data = []

    def set_style(self, style):
        self.style = style

    def add_modify(self, modify):
        self.modifies.append(modify)

    def add_header(self, header):
        self.header = header
        if self.style == 0:
            self.size += len(self.header)
            return len(self.header)
        else:
            self.size += len(self.header) * 2
            return len(self.header) *2

    def add_footer(self, footer):
        self.footer = footer
        if self.style == 0:
            self.size += len(self.footer)
            return len(self.footer)
        else:
            self.size += len(self.footer) * 2
            return len(self.footer) *2

    def process(self):
        # Load the asset from disk
        in_file = open(os.path.join(assets_path, self.name), 'rb')
        if self.style == 0:
            self.data = array.array('B')
            self.data.fromfile(in_file, self.o_size)
        else:
            self.data = array.array('H')                  # 'I' is for 32 bits integers
            self.data.fromfile(in_file, self.o_size//2)
            if self.o_size % 2:
                # odd file size... as this shouldn't happen and last byte won't be read, return a warning
                print("Warning: asset '{0}' has odd size but declared as 'unsigned int'".format(a.name))
                print("         so the last byte has been discarded")
        in_file.close()

        # do the requested modifies to the data
        for m in self.modifies:
            if m.operator == 'add':
                for cnt in range(m.length):
                    self.data[m.start+cnt] += int(m.values[cnt % len(m.values)], 0)
            elif m.operator == 'and':
                for cnt in range(m.length):
                    self.data[m.start+cnt] &= int(m.values[cnt % len(m.values)], 0)
            elif m.operator == 'or':
                for cnt in range(m.length):
                    self.data[m.start+cnt] |= int(m.values[cnt % len(m.values)], 0)
            elif m.operator == 'xor':
                for cnt in range(m.length):
                    self.data[m.start+cnt] ^= int(m.values[cnt % len(m.values)], 0)
            elif m.operator == 'set':
                for cnt in range(m.length):
                    self.data[m.start+cnt] = int(m.values[cnt % len(m.values)], 0)   # overwrites the original data with data in m.values list

        # now prepend the header
        for cnt in range(len(a.header)):
            self.data.insert(cnt, int(self.header[cnt], 0))

        # then append the footer
        for cnt in range(len(a.footer)):
            self.data.append(int(self.footer[cnt], 0))


class AssetGroup:
    def __init__(self):
        self.assets = []
        self.size = 0

    def add_asset(self, asset):
        self.assets.append(asset)
        self.size += asset.size

    def grow(self, size):
        self.size += size


class Bank:
    def __init__(self, size):
        self.assetgroups = []
        self.size = size
        self.free = size

    def add_assetgroup(self, assetgroup):
        self.assetgroups.append(assetgroup)
        self.free -= assetgroup.size


def fix_name(name):
    return name.replace('(', '_').replace(')', '_').replace(' ', '_').replace('.', '_')


def find(fun, seq):
    for item in seq:
        if fun(item):
            return item

def print_usage():
    print("Usage: assets2banks path [--firstbank=<number>[,<size>]][--compile][--singleheader[=<filename>]][--exclude=<filename>][--allowsplitting]")
    sys.exit(1)

AssetGroupList = []    # list of the groups (we will sort this)
AssetList = []         # list of the assets (for inspection)
BankList = []          # list of the banks
ExcludeList = []       # list of files to exclude

print("*** sverx's assets2banks converter ***")

if 2 <= len(sys.argv):
    assets_path = sys.argv[1]
    first_bank = 2                                                  # first bank will be number 2
    compile_rel = 0                                                 # RELs not requested
    single_h = 0                                                    # generate separate .h files
    allowsplitting = 0                                              # Allow splitting large assets in multiple parts
else:
    print_usage()

for n, arg in enumerate(sys.argv):
    if n >= 2:
        if arg[:12] == "--firstbank=":
            fb = arg[12:].split(",")
            if len(fb) > 2:
                print("Fatal: invalid firstbank parameters")
                print_usage()
            try:
                first_bank = int("+{0!s}".format(fb[0]))
                if len(fb) == 1:
                    print("Info: first bank number set to {0!s}".format(first_bank))
                else:
                    try:
                        b = Bank(int("+{0!s}".format(fb[1])))
                        BankList.append(b)
                        print("Info: first bank number set to {0!s}, size set at {1!s} bytes".format(first_bank, b.free))
                    except ValueError:
                        print("Fatal: invalid firstbank size parameter")
                        print_usage()
            except ValueError:
                print("Fatal: invalid firstbank number parameter")
                print_usage()
# deprecated --bank1size= option
# ---------- from here ----------
        elif arg[:12] == "--bank1size=":
            print("Warning: --bank1size option is deprecated. Please use --firstbank=1,<size> instead")
            try:
                b = Bank(int("+{0!s}".format(arg[12:])))
                BankList.append(b)
                first_bank = 1                                      # first bank set to 1
                print("Info: first bank number set to 1, size set at {0!s} bytes".format(b.free))
            except ValueError:
                print("Fatal: invalid bank1size parameter")
                print_usage()
# ---------- to here ----------
        elif arg == "--compile":
            compile_rel = 1
            print("Info: compiled output requested")
        elif arg == "--allowsplitting":
            allowsplitting = 1
            print("Asset splitting enabled")
        elif arg[:15] == "--singleheader=":
            single_h = 1
            single_h_filename = arg[15:]
            print("Info: single header file requested ({0!s})".format(single_h_filename))
        elif arg == "--singleheader":
            single_h = 1
            single_h_filename = "assets2banks.h"
            print("Info: single header file requested (assets2banks.h)")
        elif arg[:10] == "--exclude=":
            ExcludeList.append(arg[10:])
        else:
            print("Fatal: invalid '{0!s}' parameter".format(arg))
            print_usage()


# read cfg file (if present) and create assets and assets group accordingly
in_a_group = False
try:
    config_file = open(os.path.join(assets_path, "assets2banks.cfg"), "r").readlines()
    for l in config_file:
        ls = l.strip()
        if len(ls) == 0:                                 # if line is empty or made of just spaces, skip it
            pass
        elif ls[0] == "#":                               # if line starts with # it is a comment, we can skip it
            pass
        elif ls[0] == "{":                               # if line starts with { it means we start a group
            ag = AssetGroup()
            AssetGroupList.append(ag)
            in_a_group = True
        elif ls[0] == "}":                               # if line starts with } it means we close a group
            in_a_group = False
        elif ls[0] == ":":                               # if line starts with : it means we have an attribute
            if ls == ":format unsigned int":
                if len(a.modifies) != 0 or len(a.header) != 0 or len(a.footer) != 0:
                    print("Fatal: format attribute should be specified before any other asset attribute")
                    sys.exit(1)
                a.set_style(1)
            elif ls[:11] == ":overwrite ":
                ovp = ls[11:].split()
                try:
                    if len(ovp) == 2:                    # if there are two values only, we overwrite just one value
                        md = Modify('set', int(ovp[0], 0), 1, [ovp[1]])
                    else:
                        md = Modify('set', int(ovp[0], 0), int(ovp[1], 0), ovp[2:])
                except ValueError:
                    print("Fatal: invalid overwrite attribute parameter(s)")
                    sys.exit(1)
                a.add_modify(md)
            elif ls[:8] == ":modify ":
                mdf = ls[8:].split()
                if mdf[0].lower() == 'add' or mdf[0].lower() == 'and' or mdf[0].lower() == 'or' or mdf[0].lower() == 'xor':
                    try:
                        if len(mdf) == 2:                # if there is one value only after the operator, we modify all array elements
                            md = Modify(mdf[0].lower(), 0, a.size, [mdf[1]])
                        elif len(mdf) == 3:              # if there are two values only after the operator, we modify one array element only
                            md = Modify(mdf[0].lower(), int(mdf[1], 0), 1, [mdf[2]])
                        else:                            # if there are three (or more) values after the operator, we modify *len* array elements from *start*
                            md = Modify(mdf[0].lower(), int(mdf[1], 0), int(mdf[2], 0), mdf[3:])
                    except ValueError:
                        print("Fatal: invalid modify attribute parameter(s)")
                        sys.exit(1)
                    a.add_modify(md)
                else:
                    print("Fatal: invalid modify attribute action parameter. Only 'add', 'and', 'or' and 'xor' are valid actions")
                    sys.exit(1)
            elif ls[:8] == ":header ":
                hdp = ls[8:].split()
                ag.grow(a.add_header(hdp))
            elif ls[:8] == ":append ":
                ftp = ls[8:].split()
                ag.grow(a.add_footer(ftp))
            else:
                print("Fatal: unknown attribute '{0}'".format(ls))
                sys.exit(1)
        else:                                                   # else it's an asset
            try:
                st = os.stat(os.path.join(assets_path, str(ls)))
            except (IOError, OSError):
                print("Fatal: can't find asset '{0}'".format(ls))
                sys.exit(1)
            a = Asset(ls, st.st_size)
            AssetList.append(a)
            if not in_a_group:
                ag = AssetGroup()
                AssetGroupList.append(ag)
            ag.add_asset(a)
except (IOError, OSError):
    pass

try:
    st = os.stat(os.path.join(assets_path, "assets2banks.cfg"))  # fake asset, to skip config file, if present in folder
    a = Asset("assets2banks.cfg", st.st_size)
    AssetList.append(a)
except (IOError, OSError):
    pass

try:
    for f in os.listdir(assets_path):  # read directory content and create missing assets and assetgroup (one per asset)
        if f in ExcludeList:
            continue
        if os.path.isfile(os.path.join(assets_path, f)):
            st = os.stat(os.path.join(assets_path, f))
            a = Asset(str(f), st.st_size)
            if not find(lambda asset: asset.name == str(f), AssetList):
                AssetList.append(a)
                ag = AssetGroup()
                ag.add_asset(a)
                AssetGroupList.append(ag)
            if st.st_size == 0:
                print("Warning: {0!s} is an empty file".format(str(f)))
except (IOError, OSError):
    print("Fatal: can't access '{0}' folder".format(assets_path))
    sys.exit(1)

# At this point, all assets and groups have been created. Read the source
# data from disk and process transformations (add header/footer, etc)
for ag in AssetGroupList:
    for a in ag.assets:
        a.process()
        if (a.style == 0 and len(a.data) != a.size) or (a.style == 1 and len(a.data) != a.size/2):
            print("Fatal: Internal error")
            sys.exit(1)


AssetGroupList.sort(key=lambda g: g.size, reverse=True)    # sort the AssetGroupList by size, descending

for ag in AssetGroupList:                                  # now find a place for each assetgroup
    for b in BankList:
        if b.free >= ag.size:                              # we've found a place for this assetgroup
            b.add_assetgroup(ag)
            break
    else:                                                  # we've found no place for this assetgroup, allocate a new bank
        if ag.size <= 16384:
            b = Bank(16384)
            b.add_assetgroup(ag)
            BankList.append(b)
        else:
            if not allowsplitting:
                print("Fatal: asset group too big to fit ({1!s} bytes are needed) and splitting is not enabled.".format(ag.size))
                sys.exit(1)

            # AssetGroups are added to Banks. We want to split the current group in two or more
            # parts and add those to consecutive banks, so they are consecutive in the outputs.
            # If necessary, some assets will be split as well.

            apartgrp = AssetGroup()       # First new group

            for a in ag.assets:           # Iterate assets of original (oversized) group

                todo = a.size
                partno = 0
                offset = 0
                while offset < todo:
                    gf = 16384 - apartgrp.size  # Compute the group free space
                    if gf == 0:
                        b = Bank(16384)
                        b.add_assetgroup(apartgrp) # If it is full, it's time to commit it to a bank
                        BankList.append(b)

                        apartgrp = AssetGroup()    # Create a new group to continue...
                        gf = 16384

                    # Compute how much of the current asset we can add to the group
                    l = gf
                    if todo-offset < l:
                        l = todo-offset

                    if a.size <= gf and offset == 0:
                        apartgrp.add_asset(a)
                    else:
                        part = Asset(a.name + "_PART" + str(partno), l)
                        part.data = a.data[offset:offset+l];
                        apartgrp.add_asset(part)

                    offset += l
                    partno += 1

            if apartgrp.size > 0:
                b = Bank(16384)
                b.add_assetgroup(apartgrp)
                BankList.append(b)

# Output stage

if single_h == 1 and len(BankList)>0:
    out_file_h = open(single_h_filename, 'w')

for bank_n, b in enumerate(BankList):
    if single_h == 0:
        out_file_h = open("bank{0!s}.h".format(bank_n + first_bank), 'w')

    if compile_rel == 0:
        out_file_c = open("bank{0!s}.c".format(bank_n + first_bank), 'w')
    else:
        out_file_rel = open("bank{0!s}.rel".format(bank_n + first_bank), 'w')
        out_file_rel.write("XL3\n")

        # count the global symbols
        global_symbols = 1                              # there's already one global symbol in the header
        for ag in b.assetgroups:
            for a in ag.assets:
                global_symbols += 1

        out_file_rel.write("H A areas {0!s} global symbols\n".format(format(global_symbols, "X")))
        out_file_rel.write("M bank{0!s}\n".format(bank_n + first_bank))
        out_file_rel.write("S .__.ABS. Def000000\n")
        out_file_rel.write("A _CODE size 0 flags 0 addr 0\n")
        out_file_rel.write("A _DATA size 0 flags 0 addr 0\n")
        out_file_rel.write("A _INITIALIZED size 0 flags 0 addr 0\n")
        out_file_rel.write("A _DABS size 0 flags 8 addr 0\n")
        out_file_rel.write("A _HOME size 0 flags 0 addr 0\n")
        out_file_rel.write("A _GSINIT size 0 flags 0 addr 0\n")
        out_file_rel.write("A _GSFINAL size 0 flags 0 addr 0\n")
        out_file_rel.write("A _BANK{0!s} size {1!s} flags 0 addr 0\n".format(bank_n + first_bank,
                                                                      format(b.size - b.free, "X")))

        # list all the  global symbols
        asset_addr = 0
        for ag in b.assetgroups:
            for a in ag.assets:
                out_file_rel.write("S _{0!s} Def{1!s}\n".format(fix_name(a.name), format(asset_addr, "06X")))
                asset_addr += a.size

        out_file_rel.write("A _INITIALIZER size 0 flags 0 addr 0\n")
        out_file_rel.write("A _CABS size 0 flags 8 addr 0\n")

    asset_addr = 0
    for ag in b.assetgroups:
        for a in ag.assets:

            if a.style == 0:
                out_file_h.write("extern const unsigned char\t{0}[{1!s}];\n".format(fix_name(a.name), a.size))
                if compile_rel == 0:
                    out_file_c.write("const unsigned char {0}[{1!s}]={{\n".format(fix_name(a.name), a.size))
            else:
                out_file_h.write("extern const unsigned int\t{0}[{1!s}];\n".format(fix_name(a.name), a.size//2))
                if compile_rel == 0:
                    out_file_c.write("const unsigned int {0}[{1!s}]={{\n".format(fix_name(a.name), a.size // 2))

            out_file_h.write("#define\t\t\t\t{0}_size {1!s}\n".format(fix_name(a.name), a.size))
            out_file_h.write("#define\t\t\t\t{0}_bank {1!s}\n".format(fix_name(a.name), bank_n + first_bank))

            if compile_rel == 1:
                out_file_rel.write("T {0!s} {1!s} 00\n".format(format(asset_addr % 256, "02X"),
                                                               format(asset_addr // 256, "02X")))
                out_file_rel.write("R 00 00 07 00\n")     # this is because we mapped assets in area number 7

            ar = a.data;

            if compile_rel == 1:
                out_file_rel.write("T {0!s} {1!s} 00".format(format(asset_addr % 256, "02X"),
                                                             format(asset_addr // 256, "02X")))

            cnt = 0
            for i in range(len(ar)):
                if compile_rel == 0:
                    if a.style == 0:
                        out_file_c.write("0x{0}".format(format(ar[i], "02x")))
                    else:
                        out_file_c.write("0x{0}".format(format(ar[i], '04x')))
                else:
                    if a.style == 0:
                        out_file_rel.write(" {0!s}".format(format(ar[i], "02X")))
                        asset_addr += 1
                    else:
                        out_file_rel.write(" {0!s} {1!s}".format(format(ar[i] % 256, "02X"),
                                                                 format(ar[i] // 256, "02X")))
                        asset_addr += 2

                if compile_rel == 0:
                    cnt += 1
                    if i < len(ar)-1:
                        out_file_c.write(",")
                        if a.style == 0 and cnt == 16:
                            out_file_c.write("\n")
                            cnt = 0
                        elif a.style != 0 and cnt == 8:
                            out_file_c.write("\n")
                            cnt = 0
                else:
                    cnt += 1
                    if (a.style == 0 and cnt == 13) or (a.style != 0 and cnt == 6):   # wrap every 13 bytes (or 6 words)
                        cnt = 0

                    if cnt == 0 or i == (len(ar)-1):
                        out_file_rel.write("\n")               # EOL
                        out_file_rel.write("R 00 00 07 00\n")  # this is because we mapped assets in area number 7
                        if i < (len(ar)-1):
                            out_file_rel.write("T {0!s} {1!s} 00".format(format(asset_addr % 256, "02X"),
                                                                         format(asset_addr // 256, "02X")))
            if compile_rel == 0:
                out_file_c.write("};\n\n")

    if single_h == 0:
        out_file_h.close()

    if compile_rel == 0:
        out_file_c.close()
    else:
        out_file_rel.close()

else:
    if len(BankList) == 0:
        print("Fatal: no banks generated")
        sys.exit(1)
    else:
        print("Info: {0!s} bank(s) generated".format(len(BankList)), end="")
        for bank_n, b in enumerate(BankList):
            print(" [bank{0!s} {1!s}]".format(bank_n + first_bank, b.free), end=""),
        print(" bytes free")

if single_h == 1 and len(BankList)>0:
    out_file_h.close()
