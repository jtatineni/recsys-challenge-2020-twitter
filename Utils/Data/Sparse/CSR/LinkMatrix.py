from Utils.Data.DataStats import get_max_user_id, get_max_tweet_id
from Utils.Data.Dictionary.TweetBasicFeaturesDictArray import LinksTweetBasicFeatureDictArray
from Utils.Data.Sparse.CSR_SparseMatrix import CSR_SparseMatrix
import pandas as pd
import RootPath
import numpy as np
import scipy.sparse as sps
import time
import multiprocessing as mp


class LinkMatrix(CSR_SparseMatrix):
    """
    Abstract class representing a feature in raw format that works with csv file.
    It is needed in order to cope with NAN/NA values.
    """

    def __init__(self):
        super().__init__("tweet_link_csr_matrix")
        self.max_tweet_id = get_max_tweet_id()

    def create_matrix(self):
        nthread = 8
        nsplit = nthread * 100

        hashtag_dict = LinksTweetBasicFeatureDictArray().load_or_create()

        chunks = np.array_split(hashtag_dict, nsplit)

        pairs = [None] * nsplit
        pairs[0] = (0, chunks[0])
        for i, chunk in enumerate(chunks):
            if i is not 0:
                pairs[i] = (sum([len(c) for c in chunks[:i]]), chunk)

        with mp.Pool(nthread) as p:
            results = p.map(_compute_on_sub_array, pairs)

        tweet_list = np.concatenate([r[0] for r in results])
        hashtag_list = np.concatenate([r[1] for r in results])
        data_list = np.concatenate([r[2] for r in results])

        csr_matrix = sps.csr_matrix(
            (data_list, (tweet_list, hashtag_list)),
            shape=(self.max_tweet_id, max(hashtag_list) + 1), dtype=np.uint32)

        self.save_matrix(csr_matrix)


def _compute_on_sub_array(tuple):

    offset = tuple[0]
    subarray = tuple[1]

    tweet_list = np.array([], dtype=np.uint32)
    hashtag_list = np.array([], dtype=np.uint32)

    for tweet_id, hashtags in enumerate(subarray):

        if hashtags is not None:
            hashtag_list = np.append(
                hashtag_list,
                hashtags
            )
            tweet_list = np.append(
                tweet_list,
                np.full(len(hashtags), tweet_id)
            )

    data_list = np.full(len(hashtag_list), 1, dtype=np.uint8)

    tweet_list = tweet_list + offset

    return tweet_list, hashtag_list, data_list