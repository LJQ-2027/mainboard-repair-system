export function buildRepairEntryOptions(flows, activeFlowId) {
  return [...(flows || [])]
    .filter((flow) => flow?.flow_id && flow?.entry_label)
    .sort((left, right) => (left.entry_order ?? 999) - (right.entry_order ?? 999))
    .map((flow) => ({
      flowId: flow.flow_id,
      label: flow.entry_label,
      type: flow.entry_type || 'known_fault',
      active: flow.flow_id === activeFlowId,
    }));
}

export function resolveRepairEntryIntent(flows, flowId) {
  const flow = (flows || []).find((candidate) => candidate.flow_id === flowId);
  if (!flow?.entry_component_id) throw new RangeError(`Unknown repair entry: ${flowId}`);
  return { flowId: flow.flow_id, targetComponentId: flow.entry_component_id };
}
