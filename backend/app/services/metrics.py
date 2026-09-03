import math

def dcg(labels,k): return sum((2**rel-1)/math.log2(i+2) for i,rel in enumerate(labels[:k]))
def ndcg(labels,k):
    ideal=dcg(sorted(labels,reverse=True),k)
    return dcg(labels,k)/ideal if ideal else 0.0

def average_precision(relevant):
    hits=0; precisions=[]
    for i,rel in enumerate(relevant,1):
        if rel:
            hits+=1
            precisions.append(hits/i)
    return sum(precisions)/len(precisions) if precisions else 0.0

def metrics(labels_by_rank):
    relevant=[1 if x>=2 else 0 for x in labels_by_rank]
    total_relevant=max(sum(relevant),1)
    rr=next((1/(i+1) for i,x in enumerate(relevant) if x),0)
    return {
        'ndcg@5':round(ndcg(labels_by_rank,5),4),
        'ndcg@10':round(ndcg(labels_by_rank,10),4),
        'map':round(average_precision(relevant),4),
        'mrr':round(rr,4),
        'recall@10':round(sum(relevant[:10])/total_relevant,4),
        'recall@20':round(sum(relevant[:20])/total_relevant,4),
    }
