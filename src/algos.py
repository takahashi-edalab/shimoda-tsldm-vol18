from decimal import Decimal
from routing import entities
import numpy as np


def left_edge(netlist: list, args, n_gaps: int = None):

    gaps = []
    if not n_gaps is None:
        for i in range(n_gaps):
            gap_bottom = (i + 1) * args.gap_interval + i * args.gap_width
            gap = entities.Gap(netlist, width=args.gap_width, base_height=gap_bottom)
            gaps.append(gap)

    # left edge
    gap_count = 0
    sorted_netlist = sorted(netlist, key=lambda x: x.minx)
    assigned_gaps = []
    while sorted_netlist:
        if n_gaps is None:
            gap_bottom = (
                gap_count + 1
            ) * args.gap_interval + gap_count * args.gap_width
            gap = entities.Gap(
                sorted_netlist, width=args.gap_width, base_height=gap_bottom
            )
            assigned_gaps.append(gap)
            gap_count += 1
        else:
            unit_width_nets = [n for n in sorted_netlist if n.width == 1]
            calc_gap_congestion(gaps, unit_width_nets)
            gaps = sorted(gaps, reverse=False, key=lambda x: x.congestion)
            gap = gaps.pop(0)
            assigned_gaps.append(gap)

        while True:
            x = Decimal(float("-inf"))
            remove_nets = []
            for n in sorted_netlist:
                if x < n.minx and gap.is_assignable(n):
                    gap.assign(n)
                    x = n.maxx
                    remove_nets.append(n)

            # no assignment, go to the next gap
            if remove_nets == []:
                break

            for n in remove_nets:
                sorted_netlist.remove(n)

    return assigned_gaps


def __cap_priority(net1: entities.Net, net2: entities.Net) -> int:
    """If net1 < net2, return -1; otherwise, 1"""
    # 1st: wider
    if net1.width > net2.width:
        return -1
    elif net1.width < net2.width:
        return 1

    # 2nd: leftmost
    if net1.minx < net2.minx:
        return -1
    else:
        return 1


def is_desired_net(
    available_start_x: Decimal, density_zones: list[tuple], n: entities.Net
) -> bool:
    for z in density_zones:
        if available_start_x < z[0] and z[0] < n.minx:
            return False
    return True


def cap(netlist: list, args, n_gaps: int = None) -> list:
    from copy import deepcopy
    from collections import deque
    from functools import cmp_to_key

    sorted_netlist = deepcopy(netlist)
    sorted_netlist.sort(key=cmp_to_key(__cap_priority))

    gaps = []
    if not n_gaps is None:
        for i in range(n_gaps):
            gap_bottom = (i + 1) * args.gap_interval + i * args.gap_width
            gap = entities.Gap(netlist, width=args.gap_width, base_height=gap_bottom)
            gaps.append(gap)

    gap_count = 0
    assigned_gaps = []
    height_limit_queue = deque()
    while sorted_netlist:
        if n_gaps is None:
            gap_bottom = (
                gap_count + 1
            ) * args.gap_interval + gap_count * args.gap_width
            gap = entities.Gap(
                sorted_netlist, width=args.gap_width, base_height=gap_bottom
            )
            assigned_gaps.append(gap)
            gap_count += 1
        else:
            unit_width_nets = [n for n in sorted_netlist if n.width == 1]
            calc_gap_congestion(gaps, unit_width_nets)
            gaps = sorted(gaps, reverse=False, key=lambda x: x.congestion)
            gap = gaps.pop(0)
            assigned_gaps.append(gap)

        while True:
            # height limit
            if len(height_limit_queue) == 0:
                height_limit = None  # gap width
            else:
                height_limit = height_limit_queue[-1]

            # run Left Edge
            assign_nets = []
            x = Decimal(float("-inf"))
            # local density + zones
            zones = sorted_netlist.max_density_zones()
            # 条件を満たすnet集合を選択する
            while True:
                is_updated = False
                for n in sorted_netlist:
                    if all(
                        [
                            x < n.minx,
                            is_desired_net(x, zones, n),
                            gap.is_assignable(n, height_limit),
                        ]
                    ):
                        assign_nets.append(n)
                        x = n.maxx
                        gap.assign(n)
                        is_updated = True
                        break

                if not is_updated:
                    break

            if assign_nets == []:
                if height_limit is None:
                    break  # go to the next gap
                else:
                    # use the next height limit
                    height_limit_queue.pop()
                    continue

            # register height limit from routed nets in the round
            max_heights = sorted(
                [gap.net2assignment[net.name].max_height for net in assign_nets],
                reverse=True,
            )
            for h in max_heights:
                height_limit_queue.append(h)

            # delte nets
            for n in assign_nets:
                sorted_netlist.remove(n)
    return assigned_gaps


def calc_gap_congestion(gaps: list, netlist: list):
    def get_optimal_gaps(
        n: entities.Net, gaps: list[entities.Gap]
    ) -> list[entities.Gap]:
        gs = [g for g in gaps if n.mid_bottom_y <= g.midy and g.midy <= n.mid_upper_y]
        return gs

    def get_best_gap(n: entities.Net, gaps: list[entities.Gap]) -> entities.Gap:
        gap_heights = np.array([g.midy for g in gaps])
        diff = np.abs(gap_heights.T - np.array([n.midy])).T
        sorted_args_diff = np.argsort(diff)
        first_close_idx = sorted_args_diff[0]
        # 残りのgapが一つしかない場合には2ndは1stと同一にする
        if len(gap_heights) == 1:
            second_close_idx = first_close_idx
        else:
            second_close_idx = sorted_args_diff[1]

        # extract gaps
        first_close_gap = gaps[first_close_idx]
        second_close_gap = gaps[second_close_idx]
        # calc wirelength
        first_wl = n.vertical_wirelength(first_close_gap.midy)
        second_wl = n.vertical_wirelength(second_close_gap.midy)
        if first_wl < second_wl:
            return first_close_gap
        else:
            return second_close_gap

    # congestion初期化
    for g in gaps:
        g.congestion = 0

    # opt intervalとの重なり調査
    for n in netlist:
        opt_gaps = get_optimal_gaps(n, gaps)
        if opt_gaps == []:
            best_gap = get_best_gap(n, gaps)
            opt_gaps = [best_gap]

        for g in opt_gaps:
            g.congestion += 1 / len(opt_gaps)


def update_criticality_priority(netlist: list, gaps: list, target_gap):
    n_nets = len(netlist)

    if len(gaps) == 0:
        return np.zeros((n_nets))

    net_heights = np.array([n.midy for n in netlist])
    gap_heights = np.array([g.midy for g in gaps])
    repeat_gap_heights = np.tile(gap_heights, (n_nets, 1))
    diff = np.abs(repeat_gap_heights.T - np.array(net_heights)).T
    sorted_args_diff = np.argsort(diff)
    # 1st, 2nd closest gaps
    first_close = sorted_args_diff[:, 0]
    if len(gap_heights) == 1:
        # if #net remain is one, 2nd close one is equal to 1st clone one
        second_close = first_close
    else:
        second_close = sorted_args_diff[:, 1]

    ps = []
    for n, g1y, g2y in zip(
        netlist, gap_heights[first_close], gap_heights[second_close]
    ):
        closest_gap_wirelength = min(
            n.vertical_wirelength(g1y), n.vertical_wirelength(g2y)
        )
        target_gap_wirelength = n.vertical_wirelength(target_gap.midy)
        p = closest_gap_wirelength - target_gap_wirelength
        # update
        ps.append(p)
    return ps


def __ccap_priority(net1: entities.Net, net2: entities.Net) -> int:
    """
    Returns:
    int: -1 if net1 < net2; 1 otherwise
    """
    # wider one
    if net1.width > net2.width:
        return -1
    elif net1.width < net2.width:
        return 1

    # criticality-priority
    if net1.priority > net2.priority:
        return -1
    elif net1.priority < net2.priority:
        return 1

    # leftmost
    if net1.minx < net2.minx:
        return -1
    else:
        return 1


def ccap(org_netlist: list, args, n_gaps: int):
    from copy import deepcopy
    from functools import cmp_to_key
    from collections import deque

    netlist = deepcopy(org_netlist)
    gaps = []
    for i in range(n_gaps):
        gap_bottom = (i + 1) * args.gap_interval + i * args.gap_width
        gap = entities.Gap(netlist, width=args.gap_width, base_height=gap_bottom)
        gaps.append(gap)

    if args.gap_order[0] == "c":
        if args.gap_order.count("cf") > 0:
            congestion_first = True
        else:
            congestion_first = False

        if args.gap_order.count("allnet") > 0:
            congestion_use_allnet = True
        else:
            congestion_use_allnet = False

    elif args.gap_order == "random":
        import random

        random.seed(0)  # for random gap-order
        random.shuffle(gaps)
    elif args.gap_order == "bottom-up":
        gaps = sorted(gaps, reverse=False, key=lambda x: x.base_height)
    elif args.gap_order == "top-down":
        gaps = sorted(gaps, reverse=True, key=lambda x: x.base_height)
    else:
        raise ValueError(f"Invalid Gap Order: {args.gap_order}")

    height_limit_queue = deque()
    # start assignment
    assigned_gaps = []
    while netlist:
        if len(gaps) == 0:
            assigned_gaps = []
            break

        if args.gap_order[0] == "c" and len(gaps) > 1:
            if congestion_use_allnet:
                unit_width_nets = netlist
            else:
                unit_width_nets = [n for n in netlist if n.width == 1]

            calc_gap_congestion(gaps, unit_width_nets)
            gaps = sorted(gaps, reverse=congestion_first, key=lambda x: x.congestion)

        target_gap = gaps.pop(0)
        assigned_gaps.append(target_gap)
        # calc priority
        ps = update_criticality_priority(netlist, gaps, target_gap)
        netlist = entities.NetList([n.update_priority(p) for n, p in zip(netlist, ps)])
        # sorted netlist
        netlist.sort(key=cmp_to_key(__ccap_priority))
        while True:
            if len(height_limit_queue) == 0:
                height_limit = None  # channel width
            else:
                height_limit = height_limit_queue[-1]

            assign_nets = []
            x = Decimal(float("-inf"))
            zones = netlist.max_density_zones()

            # 1round
            while True:
                is_updated = False
                for n in netlist:
                    if (
                        x < n.minx
                        and is_desired_net(x, zones, n)
                        and target_gap.is_assignable(n, height_limit)
                    ):
                        x = n.maxx
                        target_gap.assign(n)
                        is_updated = True
                        assign_nets.append(n)
                        break

                if not is_updated:
                    break

            if assign_nets == []:
                if height_limit is None:
                    break
                else:
                    height_limit_queue.pop()
                    continue

            # register height limit
            max_heights = sorted(
                [target_gap.net2assignment[net.name].max_height for net in assign_nets],
                reverse=True,
            )
            for h in max_heights:
                height_limit_queue.append(h)

            # assignしたnet削除
            for n in assign_nets:
                netlist.remove(n)

    return assigned_gaps
