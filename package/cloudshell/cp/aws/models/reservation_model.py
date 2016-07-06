class ReservationModel(object):
    def __init__(self):
        self.reservation_id = ''
        self.owner = ''
        self.blueprint = ''
        self.domain = ''

    @staticmethod
    def create_instance_from_reservation(reservation):
        res_model = ReservationModel()
        res_model.reservation_id = reservation.reservation_id
        res_model.blueprint = reservation.environment_name
        res_model.owner = reservation.owner_user
        res_model.domain = reservation.domain
        return res_model
