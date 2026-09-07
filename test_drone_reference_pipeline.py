"""Drone scene/route regressions: test data flow, not just a Skill's wording."""
from copy import deepcopy
import json
import math
from pathlib import Path
import shutil
import uuid
import unittest
from unittest.mock import patch

from PIL import Image, ImageDraw

from design_engine import (DRONE_CAMERA_ONLY_POV_CONTRACT,
                           bind_design_source_plate_paths, normalize_design_plan,
                           sanitize_drone_still_image_request)
from design_media_service import image_workflow, _generate_request
from drone_route_engine import analyse_red_route, route_span_language
from test_design_engine import sample_design


class DroneReferencePipelineTests(unittest.TestCase):
    def setUp(self):
        cache = Path(__file__).resolve().parent / '.director_cache'
        cache.mkdir(exist_ok=True)
        # Windows sandbox users cannot reopen tempfile's owner-only (0700) dirs.
        self.root = (cache / ('drone_pipeline_' + uuid.uuid4().hex)).resolve()
        self.assertEqual(self.root.parent, cache.resolve())
        self.root.mkdir()
        self.addCleanup(shutil.rmtree, self.root)
        self.p1 = self.root / 'p1.png'
        Image.new('RGB', (320, 180), (40, 80, 140)).save(self.p1)
        self.p2 = self.root / 'p2.png'
        image = Image.new('RGB', (320, 180), 'white')
        draw = ImageDraw.Draw(image)
        draw.line([(25,150), (125,100), (65,65), (285,25)], fill='red', width=5)
        draw.ellipse((8,146,16,154), fill=(0,255,0))
        draw.ellipse((297,21,305,29), fill=(0,0,255))
        image.save(self.p2)
        self.settings = dict(checkpoint='test.safetensors', width=512, height=512, steps=8, cfg=1)
        self.inventory = [dict(media_id='P1', media_type='image', loaded=True,
                               filename='p1.png', local_path=str(self.p1), caption='Blue coastal village'),
                          dict(media_id='P2', media_type='image', loaded=True,
                               filename='p2.png', local_path=str(self.p2))]

    def plan(self, key='drone-fly-on-city'):
        return normalize_design_plan(sample_design(), {'image':9,'video':3,'audio':3},
            existing_media=self.inventory, special_skill_key=key,
            authored_requirement='按照P2飞行。只有P2闭合或我明确要求时才执行360度环绕。')

    def test_every_stage_binds_actual_p1_but_control_never_binds(self):
        for key in ('drone-fly-on-city', 'drone-fly-on-city-fireworks'):
            plan = self.plan(key)
            stages = [r for r in plan['media_requests'] if r.get('derived_from_media_id')]
            self.assertEqual(len(stages), math.ceil(plan['duration_seconds'] / 5.0))
            bind_design_source_plate_paths(stages, self.inventory)
            for stage in stages:
                self.assertEqual(stage['source_plate_local_path'],str(self.p1.resolve()))
                self.assertEqual(stage['source_plate_mode'],'p1_img2img')
                self.assertLess(stage['source_image_denoise'],.5)
            route_use = next(r for r in plan['existing_media_uses'] if r['media_id']=='P2')
            self.assertEqual(route_use['usage'],'analysis_only')
            self.assertFalse(any(r.get('immutable_scene_plate') for r in plan['media_requests']))
            self.assertEqual(stages[-1]['end_seconds'], plan['duration_seconds'])
            self.assertEqual(stages[0]['preferred_media_id'], 'P3')
            self.assertEqual(stages[0]['scene_anchor_role'], 'p3_ground_takeoff_anchor')
            self.assertEqual(stages[0]['source_image_denoise'], .15)
            self.assertTrue(all(
                row['start_seconds'] == index * 5.0
                for index, row in enumerate(stages)
            ))

    def test_explicit_360_orbit_follows_verified_p2_and_five_second_chain_scales(self):
        payload = sample_design()
        payload['duration_seconds'] = 35.0
        payload['shots'][-1]['end_seconds'] = 35.0
        plan = normalize_design_plan(
            payload, {'image': 9, 'video': 3, 'audio': 3},
            existing_media=self.inventory,
            special_skill_key='drone-fly-on-city',
            authored_requirement='以P1主题建筑为中心完成360度环绕，并严格沿P2已验证路线飞行。',
        )
        stages = [r for r in plan['media_requests'] if r.get('derived_from_media_id')]
        self.assertEqual([row['preferred_media_id'] for row in stages], [
            'P3', 'P4', 'P5', 'P6', 'P7', 'P8', 'P9',
        ])
        self.assertEqual(
            [(row['start_seconds'], row['end_seconds']) for row in stages],
            [(0.0, 5.0), (5.0, 10.0), (10.0, 15.0), (15.0, 20.0),
             (20.0, 25.0), (25.0, 30.0), (30.0, 35.0)],
        )
        camera_text = ' '.join(row['camera_movement'] for row in plan['shots'])
        self.assertIn('one complete, smooth, wide clockwise lap', camera_text)
        self.assertIn('GROUND-LAUNCH PHASE', camera_text)
        self.assertIn('LANDMARK-ORBIT PHASE', camera_text)
        self.assertIn('ROUTE-EXIT PHASE', camera_text)
        self.assertIn('follow the verified authored path', camera_text)
        self.assertIn('0 to', camera_text)
        self.assertIn('to 360 degrees', camera_text)
        self.assertIn('front-to-right-to-rear-to-left-to-front', camera_text)
        self.assertIn('strong natural parallax', camera_text)
        self.assertIn('not an in-place camera rotation', camera_text)
        self.assertIn('camera optical axis aligned', camera_text)
        self.assertIn('instantaneous forward flight tangent', camera_text)
        self.assertIn('must never independently yaw', camera_text)
        self.assertNotIn('camera aimed inward', camera_text)
        self.assertNotIn('the FPV drone', camera_text)
        self.assertTrue(all(
            DRONE_CAMERA_ONLY_POV_CONTRACT in row['additional_direction']
            for row in plan['shots']
        ))
        schedule = plan['_drone_motion_schedule']
        self.assertEqual(
            schedule['phase_completion_gate'],
            'route_must_not_begin_before_full_orbit_completion',
        )
        self.assertGreaterEqual(
            schedule['orbit_end_seconds'] - schedule['orbit_start_seconds'],
            6.0,
        )
        self.assertEqual(
            schedule['route_start_seconds'], schedule['orbit_end_seconds']
        )
        for stage in stages:
            still_text = (stage['prompt'] + ' ' + ' '.join(stage['subject_keywords'])).lower()
            self.assertNotIn('360', still_text)
            self.assertNotIn('orbit', still_text)
            self.assertNotIn('route', still_text)
            self.assertIn('colour temperature', stage['prompt'])
            self.assertIn('weather', stage['prompt'])
            self.assertIn('SCENE KEYFRAME CHAIN ANCHOR', stage['prompt'])
            self.assertIn(
                'EXCLUSIVE P1-DERIVED SCENE-STATE REPLACEMENT', stage['prompt']
            )
            self.assertIn(
                'Preserve the source-visible subject count and grouping exactly',
                stage['prompt'],
            )
            self.assertTrue(stage['single_scene_instance'])
            self.assertEqual(stage['exclusive_scene_source_media_id'], 'P1')
            self.assertIn('duplicate building', stage['negative_prompt'])

    def test_p1_pixels_are_connected_to_active_sampler_in_both_templates(self):
        template = json.loads(Path('Z-Image_Text2Image_for_webui_t2i_api.json').read_text(encoding='utf-8-sig'))
        request = dict(prompt='Blue coastal village', source_plate_mode='p1_img2img',
                       source_image_uploaded_name='stage/source.png', source_image_width=320,
                       source_image_height=176, source_image_denoise=.25)
        original = deepcopy(template)
        for graph_template in (None, template):
            graph = image_workflow(request, self.settings, 1, 'test', graph_template)
            sampler = next(n for n in graph.values() if n['class_type']=='KSampler')
            encoder = graph[sampler['inputs']['latent_image'][0]]
            self.assertEqual(encoder['class_type'],'VAEEncode')
            scale = graph[encoder['inputs']['pixels'][0]]
            loader = graph[scale['inputs']['image'][0]]
            self.assertEqual(loader['class_type'],'LoadImage')
            self.assertEqual(loader['inputs']['image'],'stage/source.png')
            self.assertEqual(sampler['inputs']['denoise'],.25)
            self.assertEqual(scale['inputs']['crop'],'disabled')
        self.assertEqual(template, original)
        with self.assertRaisesRegex(ValueError,'successful local-image upload'):
            image_workflow({**request, 'source_image_uploaded_name':''}, self.settings, 1, 'test')

    def test_generation_uploads_source_not_route_and_keeps_sky(self):
        stage = next(r for r in self.plan()['media_requests'] if r.get('derived_from_media_id'))
        item = dict(stage, local_path=str(self.root/'out.png'))
        bind_design_source_plate_paths([item], self.inventory)
        job = dict(server='http://test.invalid', http_timeout=1, poll_interval=.1, generation_timeout=1)
        def download(server, output, destination, timeout):
            Image.new('RGB',(320,176),'blue').save(destination)
        with patch('design_media_service.upload_file',return_value={'name':'uploaded.png','subfolder':'p1'}) as upload, \
             patch('design_media_service.queue_workflow',return_value='job') as queue, \
             patch('design_media_service.wait_for_history',return_value=({},[{'filename':'out.png'}])), \
             patch('design_media_service.download_image',side_effect=download), \
             patch('design_media_service.remove_solid_background') as remove:
            result = _generate_request(job,item,self.settings,None,number=1)
        self.assertEqual(upload.call_args.args[1],self.p1)
        remove.assert_not_called()
        graph = queue.call_args.args[1]
        loaders = [n['inputs']['image'] for n in graph.values() if n['class_type']=='LoadImage']
        self.assertEqual(loaders,['p1/uploaded.png'])
        self.assertTrue(result['generated'])
        with patch('design_media_service.queue_workflow') as queue:
            with self.assertRaises(FileNotFoundError):
                _generate_request(job,{**item,'source_plate_local_path':'missing.png'},self.settings,None,number=1)
            queue.assert_not_called()

    def test_direction_markers_and_bends_follow_launch_and_separate_orbit(self):
        analysis = analyse_red_route(self.p2)
        self.assertTrue(analysis['direction_verified'],analysis)
        self.assertLess(analysis['waypoints'][0]['x'],analysis['waypoints'][-1]['x'])
        motion = route_span_language(analysis,0,1)
        self.assertIn('veer right',motion)
        self.assertIn('veer left',motion)
        for leg in analysis['camera_legs']:
            self.assertIn(leg,motion)
        plan = self.plan()
        text = ' '.join(s['camera_movement'] for s in plan['shots'])
        self.assertIn('one complete, smooth, wide clockwise lap',text)
        self.assertLess(text.index('GROUND-LAUNCH PHASE'), text.index('LANDMARK-ORBIT PHASE'))
        self.assertLess(text.index('LANDMARK-ORBIT PHASE'), text.index('ROUTE-EXIT PHASE'))
        self.assertIn('veer left',text)
        self.assertNotIn('P2',text)
        schedule = plan['_drone_motion_schedule']
        self.assertEqual(schedule['takeoff_end_seconds'], 2.0)
        self.assertEqual(schedule['orbit_end_seconds'], 9.0)
        self.assertEqual(schedule['route_start_seconds'], 9.0)
        self.assertEqual(schedule['route_end_seconds'], 12.0)

        directions = ' '.join(s['additional_direction'] for s in plan['shots'])
        self.assertIn('moderate coordinated banking only', directions)
        self.assertIn('allowed only after the orbit is complete', directions)
        self.assertNotIn('banking, dives and up to 180-degree rolls', directions)

    def test_uncertain_route_never_silently_gets_a_flight_path(self):
        for shape in ('line','loop','branch','disconnected','corrupt'):
            if shape=='corrupt':
                self.p2.write_bytes(b'not an image')
            else:
                image=Image.new('RGB',(320,180),'white')
                draw=ImageDraw.Draw(image)
                if shape=='loop': draw.ellipse((40,30,250,150),outline='red',width=5)
                elif shape=='branch':
                    draw.line((25,90,280,90), fill='red',width=5)
                    draw.line((150,90,150,25), fill='red',width=5)
                elif shape=='disconnected':
                    draw.line((25,140,120,50),fill='red',width=5)
                    draw.line((180,140,280,50),fill='red',width=5)
                else: draw.line((25,150,280,25),fill='red',width=5)
                image.save(self.p2)
            analysis=analyse_red_route(self.p2)
            self.assertFalse(analysis.get('direction_verified',False))
            self.assertIn('Hold',route_span_language(analysis,0,1))
            fallback_plan = self.plan()
            camera_text = ' '.join(
                shot['camera_movement'] for shot in fallback_plan['shots']
            )
            self.assertIn('GROUND-LAUNCH PHASE', camera_text)
            self.assertIn('LANDMARK-ORBIT PHASE', camera_text)
            self.assertIn('FPV FALLBACK PHASE', camera_text)
            self.assertIn('figure-eight crossover', camera_text)
            self.assertNotIn('marked endpoint', camera_text)
            self.assertEqual(
                fallback_plan['_drone_motion_schedule']['route_mode'],
                'fpv_scene_fallback',
            )
            self.assertTrue(any('ROUTE NEEDS REVIEW' in w for w in fallback_plan['design_warnings']))

    def test_positive_still_text_cannot_prime_rings_in_either_language(self):
        request=sanitize_drone_still_image_request(dict(
            prompt='蓝色海岸村落。环绕飞行轨迹发出光带。天空清晰。 The camera makes a 360-degree orbit. Natural clouds.',
            subject_keywords=['海岸','环绕路线','orbit ring']),fireworks=True)
        for bad in ('orbit','trajectory','flight path','ring','环绕','轨迹','光带'):
            self.assertNotIn(bad,request['prompt'])
        self.assertIn('天空清晰',request['prompt'])
        self.assertIn('orbit ring',request['negative_prompt'])

    def test_repeated_normalization_does_not_accumulate_camera_directions(self):
        first = self.plan()
        second = normalize_design_plan(first, {'image':9,'video':3,'audio':3},
            existing_media=self.inventory, special_skill_key='drone-fly-on-city')
        for a,b in zip(first['shots'],second['shots']):
            self.assertEqual(a['camera_movement'],b['camera_movement'])
            self.assertEqual(b['additional_direction'].count('P1 remains the visual source'),1)

    def test_retired_tail_is_not_selected_but_pool_and_manual_images_survive(self):
        from workflow_engine import WorkflowScan, MediaAsset
        tail = MediaAsset(node_id='tail', class_type='LoadImage', media_type='image',
                          reference_id='P1', filename='tail.png')
        tail.clip_prompt = 'AUTO TERMINAL KEYFRAME. IMMUTABLE P1 SCENE PLATE.'
        tail.timeline_placed = True
        manual = deepcopy(tail)
        manual.node_id = 'manual'
        manual.clip_prompt = 'A manually authored still image.'
        scan = WorkflowScan(Path('fixture.json'), {}, [], assets=[tail, manual])
        self.assertEqual(scan.timeline_assets(), [manual])
        self.assertEqual(len(scan.assets), 2)


if __name__ == '__main__':
    unittest.main()
