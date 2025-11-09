erDiagram
    %%Person }o--|| Location : is_in
    Device }o--|| DeviceType: has
    Device }o--|| Location: is_in
    Assignment}o--||Person: assigned_from
    Device}o--||Person: assigned_to
    Person {
        string Personal-Nr UK
    }
    DeviceType {
        int dev_code uk
    }
    Location {
        int locat_code uk
    }
    Device {
        int inventar_no uk
        int dev_code fk
        int locat_code fk
    }
    Assignment {
        
    }