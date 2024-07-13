import math
import argparse
from decimal import Decimal
from numpy.random import default_rng
from routing import entities
from src import algos


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


def generate_netlist(args, chip_height=None) -> list:
    rg = default_rng(args.seed)
    # x-coord
    x_minx_maxx_list = rg.random((args.n_nets, args.max_n_pins))
    # y-coord
    if chip_height is None:
        y_minx_maxx_list = rg.random((args.n_nets, args.max_n_pins))
    else:
        y_minx_maxx_list = rg.uniform(
            0, chip_height, size=(args.n_nets, args.max_n_pins)
        )
    # width
    if args.scenario == 1:
        # normal case
        width_prob = {
            1: 0.8,
            2: 0.1,
            3: 0.08,
            4: 0.02,
        }
    elif args.scenario == 2:
        # wider one
        width_prob = {
            1: 0.5,
            2: 0.3,
            3: 0.15,
            4: 0.05,
        }
    else:
        raise ValueError(f"Invalid Scenario: {args.scenario}")
    widths = rg.choice(
        list(width_prob.keys()), size=args.n_nets, p=list(width_prob.values())
    )
    netlist = entities.NetList()
    for i, (xs, ys, width) in enumerate(
        zip(x_minx_maxx_list, y_minx_maxx_list, widths)
    ):
        # 2-8 pin nets
        n_pins = rg.choice(range(2, args.max_n_pins + 1))
        n = entities.Net(
            name=f"{i}",
            pins=[
                entities.Pin(x=Decimal(f"{x}"), y=Decimal(f"{y}"))
                for x, y in zip(xs[:n_pins], ys[:n_pins])
            ],
            width=Decimal(f"{width}"),
        )
        netlist.append(n)
    return netlist


def calc_vertical_wirelength(gaps: list) -> Decimal:
    total_wirelength = 0
    for g in gaps:
        for _, assignment in g.net2assignment.items():
            net = assignment.net
            assigned_net_midy = g.base_height + assignment.max_height - net.width / 2
            total_wirelength += net.vertical_wirelength(given_midy=assigned_net_midy)
    return total_wirelength


def main():
    args = get_args()
    dummy_netlist = generate_netlist(args)
    used_gaps = algos.left_edge(dummy_netlist, args)
    n_gaps = len(used_gaps)
    # second, re-generate netlist in the chip which has gaps used
    chip_height = (n_gaps + 1) * args.gap_interval + n_gaps * args.gap_width
    netlist = generate_netlist(args, chip_height)
    # run by each algorithm

    le_gaps = algos.left_edge(netlist, args)
    le_vwl = calc_vertical_wirelength(le_gaps)

    le_cgo_gaps = algos.left_edge(netlist, args, n_gaps)
    le_cgo_vwl = calc_vertical_wirelength(le_cgo_gaps)

    cap_gaps = algos.cap(netlist, args)
    cap_vwl = calc_vertical_wirelength(cap_gaps)

    cap_cgo_gaps = algos.cap(netlist, args, n_gaps)
    cap_cgo_vwl = calc_vertical_wirelength(cap_cgo_gaps)

    ccap_gaps = algos.ccap(netlist, args, n_gaps)
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
    print("Left Edge")
    print(f"  - #gaps used : {len(le_gaps)}")
    print(f"  - vertival wl: {le_vwl:.1f}")
    le_vwl_per_pin = le_vwl / chip_height / netlist.n_pins()
    print(f"  - vwl/Cv/|P_in|: {le_vwl_per_pin:.4f}")
    print(f"  - rate[%]      : {le_vwl_per_pin / lb_vwl_per_pin * 100:.1f}")

    print("Left Edge with CGO")
    print(f"  - #gaps used : {len(le_cgo_gaps)}")
    print(f"  - vertival wl: {le_cgo_vwl:.1f}")
    le_cgo_vwl_per_pin = le_cgo_vwl / chip_height / netlist.n_pins()
    print(f"  - vwl/Cv/|P_in|: {le_cgo_vwl_per_pin:.4f}")
    print(f"  - rate[%]      : {le_cgo_vwl_per_pin / lb_vwl_per_pin * 100:.1f}")

    print("CAP")
    print(f"  - #gaps used : {len(cap_gaps)}")
    print(f"  - vertival wl: {cap_vwl:.1f}")
    cap_vwl_per_pin = cap_vwl / chip_height / netlist.n_pins()
    print(f"  - vwl/Cv/|P_in|: {cap_vwl_per_pin:.4f}")
    print(f"  - rate[%]      : {cap_vwl_per_pin / lb_vwl_per_pin * 100:.1f}")

    print("CAP with CGO")
    print(f"  - #gaps used : {len(cap_cgo_gaps)}")
    print(f"  - vertival wl: {cap_cgo_vwl:.1f}")
    cap_cgo_vwl_per_pin = cap_cgo_vwl / chip_height / netlist.n_pins()
    print(f"  - vwl/Cv/|P_in|: {cap_cgo_vwl_per_pin:.4f}")
    print(f"  - rate[%]      : {cap_cgo_vwl_per_pin / lb_vwl_per_pin * 100:.1f}")

    print("CCAP")
    print(f"  - #gaps used : {len(ccap_gaps)}")
    print(f"  - vertival wl: {ccap_vwl:.1f}")
    ccap_vwl_per_pin = ccap_vwl / chip_height / netlist.n_pins()
    print(f"  - vwl/Cv/|P_in|: {ccap_vwl_per_pin:.4f}")
    print(f"  - rate[%]      : {ccap_vwl_per_pin / lb_vwl_per_pin * 100:.1f}")


if __name__ == "__main__":
    main()
