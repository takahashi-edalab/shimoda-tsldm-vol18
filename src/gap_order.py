import math
import argparse
from decimal import Decimal
from numpy.random import default_rng
from routing import entities
from src import algos
from src.main import generate_netlist, calc_vertical_wirelength


def get_args():
    parser = argparse.ArgumentParser(description="")
    parser.add_argument("--seed", "-s", type=int, default=0, help="random seed")
    parser.add_argument(
        "--n_nets", "-n", type=int, default=100, help="the number of nets"
    )
    parser.add_argument(
        "--max_n_pins", "-p", type=int, default=8, help="the maximum numner of pins"
    )
    parser.add_argument("--scenario", "-c", type=int, default=1, help="scenario")
    parser.add_argument("--gap_width", "-w", type=float, default=10, help="gap width")
    parser.add_argument(
        "--gap_interval", "-i", type=float, default=10, help="gap interval"
    )
    parser.add_argument(
        "--gap_order",
        "-o",
        type=str,
        default="ca-unitnet",
        choices=[
            "cf-allnet",
            "ca-allnet",
            "cf-unitnet",
            "ca-unitnet",
            "random",
            "bottom-up",
            "top-down",
        ],
        help="gap order",
    )
    args = parser.parse_args()
    return args


def main():

    args = get_args()
    dummy_netlist = generate_netlist(args)
    lb_n_gaps = math.ceil(dummy_netlist.max_density() / args.gap_width)
    chip_height = (lb_n_gaps + 1) * args.gap_interval + lb_n_gaps * args.gap_width
    netlist = generate_netlist(args, chip_height)
    # algos...
    ccap_gaps = algos.ccap(netlist, args, lb_n_gaps)
    ccap_vwl = calc_vertical_wirelength(ccap_gaps)
    # results ...
    print("Input")
    print(f"  - #nets        : {args.n_nets}")
    print(f"  - #pins        : {netlist.n_pins()}")
    print(f"  - Density      : {netlist.max_density()}")
    print("Lower Bound")
    print(f"  - #gaps used   : {math.ceil(netlist.max_density() / args.gap_width)}")
    print(f"  - horizontal wl: {netlist.horizontal_wirelength():.1f}")
    print(f"  - hwl/Ch/|N_in|: {netlist.horizontal_wirelength() / 1 / args.n_nets:.2f}")
    print(f"  - vertival   wl: {netlist.vertical_wirelength():.1f}")
    lb_vwl_per_pin = netlist.vertical_wirelength() / chip_height / netlist.n_pins()
    print(f"  - vwl/Cv/|P_in|: {lb_vwl_per_pin:.4f}")
    print(f"CCAP with {args.gap_order} gap order")
    print(f"  - #gaps used : {len(ccap_gaps)}")
    print(f"  - vertival wl: {ccap_vwl:.1f}")
    ccap_vwl_per_pin = ccap_vwl / chip_height / netlist.n_pins()
    print(f"  - vwl/Cv/|P_in|: {ccap_vwl_per_pin:.4f}")
    print(f"  - rate[%]      : {ccap_vwl_per_pin / lb_vwl_per_pin * 100:.0f}")


if __name__ == "__main__":
    main()
