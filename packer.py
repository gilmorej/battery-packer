import getopt
import sys

MAX_INT = 18446744073709551616

def pack_cells(series_count, capacities, max_pack_differential, max_difference_between_packs, capacity_target, verbose):
    done = False
    packs = {}
    pack_index = 0
    start = 0
    discarded_cells = []
    while not done:
        capacity, pack_start, pack_end = find_pack_with_capacity(capacities, start, len(capacities), max_pack_differential, capacity_target)
        if start > 0 and pack_start > 0:
            discarded_cells.extend(capacities[start:pack_start])
        packs[pack_index] = capacities[pack_start:pack_end]
        pack_index = pack_index + 1
        start = pack_end
        if pack_end == (len(capacities) - 1) or capacity == 0:
            valid_pack = validate(packs, max_pack_differential, max_difference_between_packs, series_count)
            if not valid_pack:
                capacity_target = capacity_target - 100 # Try again with a smaller target
                packs = {}
                pack_index = 0
                start = 0
                discarded_cells = []
            else:
                pack_caps = []
                i = 0
                total_cells = 0
                for key in packs.keys():
                    pack = packs[key]
                    if i > 13:
                        discarded_cells.extend(pack)
                    else:
                        total_cells = total_cells + len(pack)
                        pack_caps.append(compute_pack_capacity(pack))
                        i = i + 1
                pack_caps.sort(reverse=True)
                delta = pack_caps[0] - pack_caps[-1]
                percentage = round((delta/pack_caps[0]) * 100, 3)
                amp_hours = compute_amp_hours(packs, series_count)
                watt_hours = round(3.6 * series_count * amp_hours, 0)
                print(f"Pack is valid. Created {series_count}S {amp_hours} Ah ({watt_hours} Wh) battery pack.")
                if verbose:
                    print(f"Maximum capacity delta between packs is {delta} ({percentage}%)")
                    print(f"Total Cells: {total_cells} / {len(capacities)}")
                    print(f"Discarded Cells: {len(discarded_cells)} -> {discarded_cells}")
                done = True

def compute_amp_hours(packs, series_count):
    min_capacity = MAX_INT
    for key in packs.keys():
        if key > series_count - 1:
            break # Discard small packs at the end, if they exist
        pack = packs[key]
        computed_capacity_for_pack = compute_pack_capacity(pack)
        if min_capacity > computed_capacity_for_pack:
            min_capacity = computed_capacity_for_pack
    return round(min_capacity/1000,2)

def compute_pack_capacity(pack):
    cell_count = len(pack)
    pack_smallest_cell = min(pack)
    return cell_count * pack_smallest_cell

def find_pack_with_capacity(capacities, start, end, max_pack_differential, target):
    start_index = start
    capacity = 0
    max_capacity = 0
    result_start = 0
    result_end = 0
    # Sliding window; since the cells are sorted by capacity, the largest possible packs,
    # while restricting capacity differential between the cells will end up being cells that are beside each other
    for cell_index in range(start, end):
        if capacities[start_index] - capacities[cell_index] <= max_pack_differential:
            capacity = sum(capacities[start_index:cell_index+1])
            if capacity > target:
                # Just return the pack that meets the criteria close to the beginning of the range
                return max_capacity, result_start, result_end
            elif capacity > max_capacity:
                result_start = start_index
                result_end = cell_index + 1
                max_capacity = capacity
        else:
            # The differential between the cells became too high, so remove the first cell in the pack
            # and continue processing (slide the window)
            capacity = capacity - capacities[start_index] + capacities[cell_index]
            if capacity > target:
                # Just return the pack that meets the criteria close to the beginning of the range
                return max_capacity, result_start, result_end
            elif capacity > max_capacity:
                result_start = start_index + 1
                result_end = cell_index + 1
                max_capacity = capacity
            start_index = start_index + 1
    return max_capacity, result_start, result_end

def validate(packs, max_pack_differential, max_difference_between_packs, series_count):
    if len(packs) < series_count:
        return False
    min_cap = MAX_INT
    max_cap = 0
    success_message = ""
    for key in packs.keys():
        if key > series_count - 1:
            break # Discard small packs at the end
        pack = packs[key]
        pack_delta = pack[0] - pack[-1]
        percentage = round((pack_delta / pack[0]) * 100, 3)
        m_amp_hours = compute_pack_capacity(pack)
        success_message = success_message + f"Pack {key} (Capacity: {m_amp_hours} mAh: Delta: {pack_delta} mAh ({percentage}%)): {pack}\n"
        pack.sort()
        if abs(pack[0] - pack[-1]) > max_pack_differential:
            return False
        if m_amp_hours < min_cap:
            min_cap = m_amp_hours
        if m_amp_hours > max_cap:
            max_cap = m_amp_hours
    is_valid = (max_cap - min_cap) <= max_difference_between_packs
    if is_valid:
        print(success_message)
    return is_valid

def main(argv):
    series_count = None
    max_cell_difference_mah = None
    max_pack_difference_mah = None
    capacity_target = None
    filename = None
    verbose = False
    try:
        opts, args = getopt.getopt(argv, "hs:c:p:f:t:v:", ["series_count=", "max_cell_difference_mah=", "max_pack_difference_mah=", "csv_file_name=", "capacity_target=", "verbose="])
    except getopt.GetoptError:
        print_usage()
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print_usage()
            sys.exit(2)
        elif opt in ("-s", "--series_count"):
            series_count = int(arg)
        elif opt in ("-t", "--capacity_target"):
            capacity_target = int(arg)
        elif opt in ("-c", "--max_cell_difference_mah"):
            max_cell_difference_mah = int(arg)
        elif opt in ("-p", "--max_pack_difference_mah"):
            max_pack_difference_mah = int(arg)
        elif opt in ("-f", "--csv_file_name"):
            filename = arg
        elif opt == "-v":
            verbose = arg == 'true'

    if series_count is None or max_cell_difference_mah is None or max_pack_difference_mah is None or filename is None:
        print_usage()
        sys.exit(2)
    capacities = load_csv(filename, verbose)
    if capacity_target is None:
        # Compute the largest possible pack, given the max_pack_differential as a starting point if not specified
        capacity_target = find_pack_with_capacity(capacities, 0, len(capacities), max_pack_differential, MAX_INT)[0]
    print(f"Computing {series_count}S battery with parallel packs differing by a maximum of {max_cell_difference_mah} mAh and series packs differing by a maximum of {max_pack_difference_mah} mAh. Initial capacity target is `{capacity_target}` mAh...")
    pack_cells(series_count, capacities, max_cell_difference_mah, max_pack_difference_mah, capacity_target, verbose)

def load_csv(filename, verbose):
    # Each line is a integer capacity.
    # May enhance in the future to provide better packing details, or to remove cells with high resistance.
    file = open(filename, 'r')
    lines = file.readlines()
    capacities = []
    for line in lines:
        capacities.append(int(line.rstrip()))
    capacities.sort(reverse=True)
    if verbose:
        print(f"Loaded {len(capacities)} capacities from CSV:")
        print(capacities)
    return capacities

def print_usage():
    print('Usage: packer.py --csv_file_name=<CSV file of capacities> --series_count=<number of cells in series> --max_cell_difference_mah=<maximum difference in capacity (mAh) between parallel cells> --max_pack_difference_mah=<maximum difference in capacity (mAh) between series packs>')
    print('Use `-v` or `--verbose` for verbose output')
    print('Example: python3 packer.py -csv_file_name=capacities.csv -s=14 --max_cell_difference_mah=100 --max_pack_difference_mah=2200')
    print('Example: python3 packer.py -f capacities.txt -s 14 -c 100 -p 2200')

if __name__ == "__main__":
    main(sys.argv[1:])
