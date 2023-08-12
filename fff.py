def func():
    try:
        if 1 == 1:
            raise TypeError('current_date')
    except TypeError as error:
        print(error.args)
    #    print(dir(error))
    #    print('*'*150)
    #    print(error.__new__)


func()
