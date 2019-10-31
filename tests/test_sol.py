# Copyright (c) 2019 Alethea Flowers for Winterbloom
# Licensed under the MIT License

import math
from unittest import mock

import usb_midi
import winterbloom_smolmidi as smolmidi
from winterbloom_sol import sol


class TestState:
    def test_default_state(self):
        state = sol.State()

        assert state.message is None
        assert state.note is None
        assert state.velocity == 0
        assert state.pitch_bend == 0
        assert state.pressure == 0
        for n in range(128):
            assert state.cc[n] == 0

    def test_copy_from(self):
        state_a = sol.State()
        state_b = sol.State()

        state_a.message = object()
        state_a.note = 42
        state_a.velocity = 43
        state_a.pitch_bend == 45
        state_a.pressure == 46
        for n in range(128):
            state_a.cc[n] = n

        state_b.copy_from(state_a)

        assert state_b.message is state_a.message
        assert state_b.note == state_a.note
        assert state_b.velocity == state_a.velocity
        assert state_b.pitch_bend == state_a.pitch_bend
        assert state_b.pressure == state_a.pressure
        for n in range(128):
            assert state_b.cc[n] == state_a.cc[n]

        # Check for deep copy
        state_a.cc[0] = 100
        assert state_b.cc[0] != state_a.cc[0]


class TestOutputs:
    def test_default_state(self):
        outputs = sol.Outputs()

        assert outputs.cv_a == 0.0
        assert outputs.cv_b == 0.0
        assert outputs.gate_1 is False
        assert outputs.gate_2 is False
        assert outputs.gate_3 is False
        assert outputs.gate_4 is False

        assert str(outputs) == "<Outputs A:0, B:0, 1:False, 2:False, 3:False, 4:False>"

    def test_drive_cv_outs(self):
        outputs = sol.Outputs()

        outputs.cv_a = 10.0
        outputs.cv_b = 10.0

        assert outputs.cv_a == 10.0
        assert outputs.cv_b == 10.0

        assert outputs._cv_a._analog_out._driver.spi_device.spi.data

    @mock.patch("time.monotonic", autospec=True)
    def test_trigger_step(self, time_monotonic):
        outputs = sol.Outputs()

        time_monotonic.return_value = 0
        outputs.trigger_gate_1()
        outputs.trigger_gate_2(False)

        time_monotonic.return_value = 0.014
        outputs.step()
        assert outputs.gate_1 is True
        assert outputs.gate_2 is False

        time_monotonic.return_value = 0.016
        outputs.step()
        assert outputs.gate_1 is False
        assert outputs.gate_2 is True


class TestSol:
    def test_default_state(self):
        sol.Sol()

    def test_run_loop_simple(self):
        def loop(previous, current, outputs):
            assert previous.note is None
            assert current.note == 42
            assert math.isclose(current.velocity, 0.5, rel_tol=0.01)

            outputs.gate_1 = True

            raise sol._StopLoop

        # Add data to the midi stub
        usb_midi.ports[0].data = iter([smolmidi.NOTE_ON, 42, 64])

        s = sol.Sol()
        s.run(loop)

        assert s.outputs.gate_1 is True

    def test_run_loop_note_on_note_off(self):
        count = 0

        def loop(previous, current, outputs):
            nonlocal count

            if count == 0:
                assert previous.note is None
                assert current.note == 42
            elif count == 1:
                assert previous.note == 42
                assert current.note is None
            else:
                raise sol._StopLoop

            count += 1

        # Add data to the midi stub
        usb_midi.ports[0].data = iter(
            [smolmidi.NOTE_ON, 42, 64, smolmidi.NOTE_OFF, 42, 0]
        )

        s = sol.Sol()
        s.run(loop)

        assert count == 2
