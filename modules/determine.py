"""
Deterministic helpers and/or classes for Bismuth PoS
"""

# Third party modules
import random
import time
import math
import asyncio

# Custom modules
import common
import poscrypto

__version__ = '0.0.2'

# local verbose switch
VERBOSE = True

REF_ADDRESS = ''

# NOTE: I used distance between hashes to order the MNs, but it may be simpler
# to use random, seeded with previous hash, then random.shuffle()
# TODO: perf tests.
"""
Warning : "Note that even for small len(x), the total number of permutations of x can quickly grow larger than the period of most random number generators. 
This implies that most permutations of a long sequence can never be generated. For example, a sequence of length 2080 is 
the largest that can fit within the period of the Mersenne Twister random number generator."

"""

# Helpers  ###########################################################


def my_distance(address):
    """
    Return the Hamming distance between an address and the ref hash, that was converted to be address like
    :param string:
    :return:
    """
    global REF_ADDRESS
    # distance = sum(bin(i ^ j).count("1") for i, j in zip(address[0].encode('ascii'), REF_HASH.encode('ascii')))
    # Start with a distance of zero, and count up
    distance = 0
    # Loop over the indices of the string
    for i in range(34):
        # addresses are 34 char long
        distance += abs(ord(address[0][i]) - ord(REF_ADDRESS[i]))
        # Better results (spread) than pure bin hamming
    if VERBOSE:
        print(address, distance)
    return distance


# List and tickets management  ###############################################


async def mn_list_to_tickets(mn_list):
    """
    :param mn_list: list of mn with properties
    :return: list of tickets for delegates determination
    """
    # mn_list is supposed to be ordered the same for everyone
    tickets = []
    # If we have less candidates than seats, re-add the list until we have enough.
    # Always parse the full list even if this means adding too many candidates
    # (this ensures everyone gets the same chance)
    id = 0
    while len(tickets) < common.MAX_ROUND_SLOTS:
        for mn in mn_list:
            # a more compact and faster version can be written, I prefer to aim at clarity
            for chances in range(mn[3]):  # index 3 is the weight
                tickets.append((mn[0], id))
                id += 1
    return tickets


async def tickets_to_delegates(tickets_list, reference_hash):
    """
    Order and extract only the required number of candidates from the tickets
    :param tickets_list:
    :param reference_hash:
    :return:
    """
    # Set the reference Hash
    global REF_ADDRESS
    REF_ADDRESS = poscrypto.hash_to_addr(reference_hash)
    # sort the tickets according to their hash distance.
    tickets_list.sort(key=my_distance)
    if VERBOSE:
        #print("Ref Hash Bin", REF_HASH_BIN)
        print("Sorted Tickets:\n", tickets_list)
    return tickets_list[:common.MAX_ROUND_SLOTS]


def pick_two_not_in(address_list, avoid):
    """
    Pick a random couple of mn not in avoid
    :param mn_list:
    :param here:
    :param nor:
    :return:
    """
    candidates = [a for a in address_list if a not in avoid]
    if len(candidates) < 2:
        return None
    # random sampling without replacement
    return random.sample(candidates, 2)


async def mn_list_to_test_slots(full_mn_list, forge_slots):
    """
    Predict tests to be run during each slot, but avoid testing forging MN
    :param mn_list:
    :param forge_slots:
    :return: list with list of tests for each slot.
    """
    global REF_ADDRESS
    # TODO: are we 100% sure random works the same on all python/os? prefer custom impl?
    """
    https://docs.python.org/3/library/random.html
    Most of the random module’s algorithms and seeding functions are subject to change across Python versions, but two aspects are guaranteed not to change:
    If a new seeding method is added, then a backward compatible seeder will be offered.
    The generator’s random() method will continue to produce the same sequence when the compatible seeder is given the same seed.
    """
    # TODO: test and have a custom impl to be sure?
    # This is what ensures everyone shuffles the same way.
    random.seed(REF_ADDRESS)
    # Just keep the pubkeys/addresses, no dup here whatever the weight.
    all_mns_addresses = [mn[0] for mn in full_mn_list]
    test_slots = []
    for slot in forge_slots:
        # slot is a tuple (address, ticket#)
        tests = []
        avoid = [slot[0]]
        while len(tests) < common.TESTS_PER_SLOT:
            picks = pick_two_not_in(all_mns_addresses, avoid)
            if not picks:
                # not enough mn left to do the required tests.
                # TODO: this should be an alert since we will lack messages.
                break
            # also pick a random test
            test_type = random.choice(common.TESTS_TYPE)
            tests.append((picks[0], picks[1], test_type))
        test_slots.append(tests)
    return test_slots


# Timeslots helpers ###########################################################


def timestamp_to_round_slot(ts=0):
    """
    Given a timestamp, returns the specific round and slot# that fits.
    :param ts: timestamp to use. If 0, will use current time
    :return: tuple (round, slot in round)
    """
    if ts == 0 :
        ts = time.time()
    the_round = math.floor((ts - common.ORIGIN_OF_TIME) / common.ROUND_TIME_SEC)
    round_start = common.ORIGIN_OF_TIME + the_round * common.ROUND_TIME_SEC
    the_slot = math.floor((ts - round_start) / common.POS_SLOT_TIME_SEC)
    return the_round, the_slot


# TODO: time_to_next_slot

# TODO: time_to_next_round


async def get_connect_to(peers, round, address):
    """
    Sends back the list of peers to connect to
    :param peers:
    :param round:
    :param address:
    :return:
    """
    # Todo: Should peers stay in params? better be known by determine, since they will be collected and stored for each round.
    # POC: sends a subset of the peers, excluding us.
    # Unique seed for a peer and a round
    random.seed(address+str(round))
    # remove our address - We could also keep it, but not connect to if it's in the list (allows same list for everyone)
    result = [peer for peer in peers if peer[0] != address]
    # TODO: test for this shuffle, make sure it always behaves the same.
    random.shuffle(result)
    # POC: limit to 2 peers
    # return result[:2]
    # Temp test with 2 nodes only
    if "BLYkQwGZmwjsh7DY6HmuNBpTbqoRqX14ne" == address:
        return [peers[1]]
    return [peers[0]]


if __name__ == "__main__":
    print("I'm a module, can't run!")