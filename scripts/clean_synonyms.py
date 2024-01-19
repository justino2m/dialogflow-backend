from google.cloud import datastore

SYNONYM_KIND = "Synonyms"
FAQ_KIND = "FAQs"

client = datastore.Client()

def clean_synonym_kind():
    query = client.query(kind=SYNONYM_KIND)
    all_syns = query.fetch()

    updated_syns = []
    old_values = []
    for s in all_syns:
        value = s['value']

        if value.endswith(' ') or value.startswith(' '):
            old_values.append(value)
            print(f"Found synonym: {value}")
            s['value'] = s['value'].strip()
            updated_syns.append(s)

    print("About to update the following synonym values from")
    print(old_values)
    print("to")
    print([s['value'] for s in updated_syns])
    confirm = input(f"Clean synonyms for {client.project}? (y/n)")
    if confirm == "y":
        client.put_multi(updated_syns)
        print("Cleaned synonyms")



def clean_faq_kind():
    query = client.query(kind=FAQ_KIND)
    all_faqs = query.fetch()

    str_faqs, list_faqs = [], []
    updated_topics = []
    for f in all_faqs:
        if f.get('synonyms') is None:
            print(f"FAQ {f['name']} has no synonyms")
            continue
        print(type(f['synonyms']))
        if isinstance(f['synonyms'], str):
            str_faqs.append(f['name'])
        if isinstance(f['synonyms'], list):
            list_faqs.append(f['name'])


    print(f"string FAQS: {len(str_faqs)}")
    print(f"list FAQS: {len(list_faqs)}")
    print(str_faqs)
        # for s in f['synonyms']:
        #     print(s)
        #     if s.endswith(' ') or s.startswith(' '):
        #         print(s)
        #         print("**************************")
        #         print(f['name'])
        #         print(f['synonyms'])
        #         print(f"Found FAQ {f['name']} synonym: {s}")
        #         print()

if __name__ == "__main__":
    confirm = input(f"Continue for {client.project}? (y/n) > ")
    if confirm == "y":
        clean_synonym_kind()
        # clean_faq_kind()



