import os

import m5
from m5.objects import *

m5.util.addToPath("../")

from caches import (
    L1DCache,
    L1ICache,
    L2Cache,
)
from common import SimpleOpts

from cpu import MyMinorCPU

from gem5.resources.resource import obtain_resource

SimpleOpts.add_option("--clk", help="System clock frequency", default="1GHz")
SimpleOpts.add_option("--fpu_operation_latency", default="6")
SimpleOpts.add_option("--fpu_issue_latency", default="1")
SimpleOpts.add_option("--cmd", help="Binary to run in SE mode", default="")
SimpleOpts.add_option("--options", help="Arguments for the binary", default="")
SimpleOpts.add_option("--resource", help="gem5 resource ID", default="")

args = SimpleOpts.parse_args()

res = obtain_resource(resource_id=args.resource)
print(f"Resource: {args.resource}")
binary = res.get_local_path()


class L3Cache(L2Cache):
    def __init__(self, args=None):
        super().__init__(args)
        self.size = "2MiB"
        self.assoc = 16


system = System()
system.clk_domain = SrcClockDomain()
system.clk_domain.clock = args.clk
system.clk_domain.voltage_domain = VoltageDomain()
system.mem_mode = "atomic"
system.mem_ranges = [AddrRange("8192MiB")]

system.cpu = X86AtomicSimpleCPU()

system.cpu.icache = L1ICache(args)
system.cpu.dcache = L1DCache(args)
system.cpu.icache.connectCPU(system.cpu)
system.cpu.dcache.connectCPU(system.cpu)

system.l2bus = L2XBar()
system.l3bus = L2XBar()
system.membus = SystemXBar()

system.cpu.icache.connectBus(system.l2bus)
system.cpu.dcache.connectBus(system.l2bus)

system.l2cache = L2Cache(args)
system.l2cache.connectCPUSideBus(system.l2bus)
system.l2cache.connectMemSideBus(system.l3bus)

system.l3cache = L3Cache(args)
system.l3cache.connectCPUSideBus(system.l3bus)
system.l3cache.connectMemSideBus(system.membus)

system.cpu.createInterruptController()
system.cpu.interrupts[0].pio = system.membus.mem_side_ports
system.cpu.interrupts[0].int_requestor = system.membus.cpu_side_ports
system.cpu.interrupts[0].int_responder = system.membus.mem_side_ports

system.system_port = system.membus.cpu_side_ports

system.mem_ctrl = MemCtrl()
system.mem_ctrl.dram = HBM_2000_4H_1x64()
system.mem_ctrl.dram.range = system.mem_ranges[0]
system.mem_ctrl.port = system.membus.mem_side_ports

system.workload = SEWorkload.init_compatible(binary)

process = Process()
process.cmd = [binary] + args.options.split()
system.cpu.workload = process
system.cpu.createThreads()

root = Root(full_system=False, system=system)
m5.instantiate()

print("Beginning simulation!")
exit_event = m5.simulate()
print(f"Exiting @ tick {m5.curTick()} because {exit_event.getCause()}")
