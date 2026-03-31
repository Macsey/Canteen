import unittest

from models import Student, Table, Window


class TestStudent(unittest.TestCase):
    def test_state_transition_service_to_waiting_seat(self):
        student = Student(id=1, arrival_time=0)
        student.start_service(current_tick=0, service_duration=2)

        self.assertEqual(student.status, "serving")
        self.assertIsNone(student.update_state_on_tick())
        event = student.update_state_on_tick()
        self.assertEqual(event, "service_finished")
        self.assertEqual(student.status, "waiting_seat")

    def test_state_transition_eating_to_finished(self):
        student = Student(id=2, arrival_time=0)
        student.start_eating(current_tick=1, eating_duration=2, seat_position=(0, 0))

        self.assertEqual(student.status, "eating")
        self.assertIsNone(student.update_state_on_tick())
        event = student.update_state_on_tick()
        self.assertEqual(event, "eating_finished")
        self.assertEqual(student.status, "finished")


class TestWindow(unittest.TestCase):
    def test_window_queue_and_service(self):
        window = Window(id=0)
        s1 = Student(id=1, arrival_time=0)
        s2 = Student(id=2, arrival_time=0)

        window.enqueue(s1)
        window.enqueue(s2)
        self.assertEqual(window.queue_length(), 2)

        finished = window.handle_service_tick(current_tick=0, service_time_sampler=lambda: 1)
        self.assertIsNotNone(finished)
        self.assertEqual(finished.id, 1)
        self.assertEqual(window.total_served, 1)
        self.assertEqual(window.queue_length(), 1)


class TestTable(unittest.TestCase):
    def test_occupy_and_release(self):
        table = Table(rows=1, cols=1, capacity_per_unit=2)

        seat1 = table.occupy_seat(prefer_shared=False)
        seat2 = table.occupy_seat(prefer_shared=True)
        seat3 = table.occupy_seat(prefer_shared=True)

        self.assertIsNotNone(seat1)
        self.assertIsNotNone(seat2)
        self.assertIsNone(seat3)
        self.assertEqual(table.available_count(), 0)

        self.assertTrue(table.release_seat((0, 0)))
        self.assertEqual(table.available_count(), 1)

    def test_release_invalid_position(self):
        table = Table(rows=1, cols=1, capacity_per_unit=2)
        self.assertFalse(table.release_seat((2, 2)))


if __name__ == "__main__":
    unittest.main(verbosity=2)
