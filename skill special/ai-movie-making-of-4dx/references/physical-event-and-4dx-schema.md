# Physical Event and 4DX Event Contract

Physical Event minimum fields: `event_id`, `source_shot_id`, `event_type`, `start_ms`, `duration_ms`, `magnitude`, `source`, `target`, `direction`, `onset`, `decay`, `material_response`, `screen_plane_bridge`, `audience_reaction_trigger`, `status`, `generated_by`.

4DX Event minimum fields: `event_id`, `physical_event_id`, `effect_id`, `start_ms`, `duration_ms`, `intensity`, `density`, `actuator_intent`, `camera_motion_is_source`, `generated_by`, `status`.

The two records are separate. `physical_event_id` is the only causal link and `camera_motion_is_source` must remain false. In this live-auditorium showcase, every selected effect owns a chapter whose screen cause, theatre mechanism and audience response remain active together for a target of 99% of the chapter. Every selected effect therefore produces one linked planned event whose duration covers that active interval. Deselected effects produce no chapter and no automatic event. Manual Timeline events are preserved.

`experience_design.rules` additionally records `voice_over_policy=off`, `sound_source_policy=diegetic_4dx_auditorium_only`, `audience_reaction_required=true`, `screen_plane_breakout_required=true`, `screen_border_occlusion_required=true`, `audience_startle_causality_required=true`, `duplicate_source_subject_forbidden=true`, `effect_visible_runtime_target=0.99`, `fpv_audience_orbit_required=true` and `fpv_in_place_spin_forbidden=true`.
