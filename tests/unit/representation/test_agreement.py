from noggin.representation.agreement import Agreement


def test_agreement(dummy_agreement_dict):
    """Test the Agreement representation"""
    agreement = Agreement(dummy_agreement_dict)
    assert agreement.name == "CentOS Agreement"
    assert agreement.description == "Particularly \nsing purpose \nhere"
    assert agreement.users == [
        'andrew0',
        'austin5',
        'terri10',
        'austin15',
        'brittney20',
        'logan25',
        'tracy30',
        'alexis35',
        'james40',
        'julie45',
    ]
    assert agreement.groups == ["designers"]
    assert agreement.enabled is True


def test_agreement_disabled(dummy_agreement_dict):
    """Test the Agreement representation when disabled"""
    dummy_agreement_dict["ipaenabledflag"] = ["FALSE"]
    agreement = Agreement(dummy_agreement_dict)
    assert agreement.enabled is False
