import json
from jsondiff import diff

# Φόρτωση των δύο αρχείων
with open('tiny-secp256k1-withflags.json', 'r') as f1:
    with_flags = json.load(f1)

with open('tiny-secp256k1-noflags.json', 'r') as f2:
    no_flags = json.load(f2)

# Σύγκριση των αρχείων
# Το syntax='symmetric' δείχνει ξεκάθαρα τι υπάρχει στο ένα και λείπει από το άλλο
differences = diff(no_flags, with_flags, syntax='symmetric')


#set_with = set(tuple(x) for x in with_flags['call2fun'])
#set_no = set(tuple(x) for x in no_flags['call2fun'])

#added = set_with - set_no
#removed = set_no - set_with

#print("Κλήσεις που υπάρχουν ΜΟΝΟ στο withflags:", added)


print("defferences", differences)
print(f"Συνολικές κλήσεις (withflags): {len(with_flags['fun2fun'])}")
print(f"Συνολικές κλήσεις (noflags): {len(no_flags['fun2fun'])}")
print(f"Συνολικά functions (with flags): {len(with_flags['functions'])}")
print(f"Συνολικά functions (no flags): {len(no_flags['functions'])}")
print(f"Διαφορά(fun2fun): {len(with_flags['fun2fun']) - len(no_flags['fun2fun'])}")
print(f"Συνολικά call2fun (with flags): {len(with_flags['call2fun'])}")
print(f"Συνολικά call2fun (no flags): {len(no_flags['call2fun'])}")
